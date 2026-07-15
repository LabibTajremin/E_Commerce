import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
def app(database_url: str, redis_url: str, _run_migrations: None):
    import src.core.config as config_module

    config_module.settings.database_url = database_url
    config_module.settings.redis_url = redis_url
    import src.infrastructure.db.session as session_module

    session_module.engine = session_module.create_engine(database_url)
    session_module.async_session_factory = session_module.async_sessionmaker(
        session_module.engine, expire_on_commit=False, autoflush=False
    )

    import src.infrastructure.cache.redis_client as redis_client_module

    redis_client_module.get_redis.cache_clear()

    from src.main import app as fastapi_app

    return fastapi_app


async def _register_and_login_owner(client: httpx.AsyncClient, subdomain: str) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": subdomain,
            "subdomain": subdomain,
            "owner_email": f"owner@{subdomain}.com",
            "owner_password": "hunter22!!",
        },
        headers={"host": "platform.localhost"},
    )
    login_resp = await client.post(
        "/api/v1/admin/auth/login",
        json={"email": f"owner@{subdomain}.com", "password": "hunter22!!"},
        headers={"host": f"{subdomain}.localhost"},
    )
    return str(login_resp.json()["access_token"])


async def test_full_checkout_flow_creates_order_and_decrements_stock(
    app, db_session: AsyncSession
) -> None:
    subdomain = "e2e-checkout-a"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await _register_and_login_owner(client, subdomain)
        owner_headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {owner_token}"}
        public_headers = {"host": f"{subdomain}.localhost"}

        product_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Checkout Widget", "price": "15.00", "stock_qty": 3},
            headers=owner_headers,
        )
        product = product_resp.json()
        await client.post(
            "/api/v1/admin/products/bulk-status",
            json={"product_ids": [product["id"]], "status": "published"},
            headers=owner_headers,
        )

        register_resp = await client.post(
            "/api/v1/storefront/customers/register",
            json={"email": "shopper@example.com", "password": "hunter22!!", "name": "Shopper"},
            headers=public_headers,
        )
        assert register_resp.status_code == 201
        customer_token = register_resp.json()["access_token"]
        customer_headers = {**public_headers, "Authorization": f"Bearer {customer_token}"}

        add_item_resp = await client.post(
            "/api/v1/storefront/cart/items",
            json={"product_id": product["id"], "quantity": 2},
            headers=customer_headers,
        )
        assert add_item_resp.status_code == 200
        assert add_item_resp.json()["line_items"][0]["quantity"] == 2

        checkout_resp = await client.post(
            "/api/v1/storefront/checkout",
            json={
                "shipping_address": {
                    "line1": "1 Main St",
                    "city": "Metropolis",
                    "state": "CA",
                    "postal_code": "90210",
                    "country": "US",
                }
            },
            headers=customer_headers,
        )
        assert checkout_resp.status_code == 201, checkout_resp.text
        order = checkout_resp.json()
        assert order["status"] == "pending"
        assert order["subtotal"] == "30.00"

        subtotal = 30.00
        tax = round(subtotal * 0.08, 2)
        shipping = 5.00  # below the $50 free-shipping threshold
        expected_total = round(subtotal + tax + shipping, 2)
        assert float(order["total"]) == expected_total

        cart_after_resp = await client.get("/api/v1/storefront/cart", headers=customer_headers)
        assert cart_after_resp.json()["line_items"] == []

        product_after_resp = await client.get(
            f"/api/v1/admin/products/{product['id']}", headers=owner_headers
        )
        assert product_after_resp.json()["stock_qty"] == 1

        my_orders_resp = await client.get("/api/v1/storefront/orders", headers=customer_headers)
        assert my_orders_resp.json()["total"] == 1

        admin_order_resp = await client.get(
            f"/api/v1/admin/orders/{order['id']}", headers=owner_headers
        )
        assert admin_order_resp.status_code == 200

        transition_resp = await client.patch(
            f"/api/v1/admin/orders/{order['id']}/status",
            json={"status": "paid"},
            headers=owner_headers,
        )
        assert transition_resp.status_code == 200
        assert transition_resp.json()["status"] == "paid"


async def test_checkout_with_insufficient_stock_returns_409(app, db_session: AsyncSession) -> None:
    subdomain = "e2e-checkout-b"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await _register_and_login_owner(client, subdomain)
        owner_headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {owner_token}"}
        public_headers = {"host": f"{subdomain}.localhost"}

        product_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Scarce Widget", "price": "5.00", "stock_qty": 1},
            headers=owner_headers,
        )
        product = product_resp.json()

        register_resp = await client.post(
            "/api/v1/storefront/customers/register",
            json={"email": "greedy@example.com", "password": "hunter22!!", "name": "Greedy"},
            headers=public_headers,
        )
        customer_headers = {
            **public_headers,
            "Authorization": f"Bearer {register_resp.json()['access_token']}",
        }

        await client.post(
            "/api/v1/storefront/cart/items",
            json={"product_id": product["id"], "quantity": 5},
            headers=customer_headers,
        )

        checkout_resp = await client.post(
            "/api/v1/storefront/checkout",
            json={
                "shipping_address": {
                    "line1": "1 Main St",
                    "city": "Metropolis",
                    "state": "CA",
                    "postal_code": "90210",
                    "country": "US",
                }
            },
            headers=customer_headers,
        )
        assert checkout_resp.status_code == 409


async def test_customer_cannot_see_another_customers_order(app, db_session: AsyncSession) -> None:
    subdomain = "e2e-checkout-c"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await _register_and_login_owner(client, subdomain)
        owner_headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {owner_token}"}
        public_headers = {"host": f"{subdomain}.localhost"}

        product_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Shared Widget", "price": "5.00", "stock_qty": 5},
            headers=owner_headers,
        )
        product = product_resp.json()

        reg_a = await client.post(
            "/api/v1/storefront/customers/register",
            json={"email": "a@example.com", "password": "hunter22!!", "name": "A"},
            headers=public_headers,
        )
        headers_a = {**public_headers, "Authorization": f"Bearer {reg_a.json()['access_token']}"}
        reg_b = await client.post(
            "/api/v1/storefront/customers/register",
            json={"email": "b@example.com", "password": "hunter22!!", "name": "B"},
            headers=public_headers,
        )
        headers_b = {**public_headers, "Authorization": f"Bearer {reg_b.json()['access_token']}"}

        await client.post(
            "/api/v1/storefront/cart/items",
            json={"product_id": product["id"], "quantity": 1},
            headers=headers_a,
        )
        checkout_resp = await client.post(
            "/api/v1/storefront/checkout",
            json={
                "shipping_address": {
                    "line1": "1 Main St",
                    "city": "Metropolis",
                    "state": "CA",
                    "postal_code": "90210",
                    "country": "US",
                }
            },
            headers=headers_a,
        )
        order_id = checkout_resp.json()["id"]

        cross_resp = await client.get(f"/api/v1/storefront/orders/{order_id}", headers=headers_b)
        assert cross_resp.status_code == 403
