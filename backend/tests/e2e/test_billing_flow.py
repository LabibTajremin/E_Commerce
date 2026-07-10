import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.payment_gateway import WebhookEvent
from tests.unit.application.fakes import FakePaymentGateway


@pytest.fixture
def app_and_gateway(database_url: str, redis_url: str, _run_migrations: None):
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
    from src.presentation.dependencies import get_payment_gateway

    # Never hit real Stripe over the network in tests — substitute a fake
    # gateway for the whole app via FastAPI's dependency override mechanism.
    fake_gateway = FakePaymentGateway()
    fastapi_app.dependency_overrides[get_payment_gateway] = lambda: fake_gateway

    yield fastapi_app, fake_gateway

    fastapi_app.dependency_overrides.clear()


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


async def test_order_pay_returns_checkout_url_from_gateway(
    app_and_gateway, db_session: AsyncSession
) -> None:
    app, fake_gateway = app_and_gateway
    subdomain = "e2e-bill-a"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await _register_and_login_owner(client, subdomain)
        owner_headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {owner_token}"}
        public_headers = {"host": f"{subdomain}.localhost"}

        product_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Payable Widget", "price": "20.00", "stock_qty": 5},
            headers=owner_headers,
        )
        product = product_resp.json()
        await client.post(
            "/api/v1/admin/products/bulk-status",
            json={"product_ids": [product["id"]], "status": "published"},
            headers=owner_headers,
        )

        reg = await client.post(
            "/api/v1/storefront/customers/register",
            json={"email": "buyer@example.com", "password": "hunter22!!", "name": "Buyer"},
            headers=public_headers,
        )
        customer_headers = {
            **public_headers,
            "Authorization": f"Bearer {reg.json()['access_token']}",
        }
        await client.post(
            "/api/v1/storefront/cart/items",
            json={"product_id": product["id"], "quantity": 1},
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
        order = checkout_resp.json()

        pay_resp = await client.post(
            f"/api/v1/storefront/orders/{order['id']}/pay",
            json={"success_url": "https://shop.test/ok", "cancel_url": "https://shop.test/cancel"},
            headers=customer_headers,
        )

        assert pay_resp.status_code == 200
        assert pay_resp.json()["checkout_url"].startswith("https://checkout.stripe.test/")
        assert fake_gateway.checkout_calls[0]["order_id"] == order["id"]


async def test_webhook_marks_order_paid_and_is_idempotent_on_replay(
    app_and_gateway, db_session: AsyncSession
) -> None:
    """DoD: webhook handler is idempotent — replaying the same event twice has
    no duplicate side effects, exercised end-to-end over real HTTP + Postgres."""
    app, fake_gateway = app_and_gateway
    subdomain = "e2e-bill-b"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await _register_and_login_owner(client, subdomain)
        owner_headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {owner_token}"}
        public_headers = {"host": f"{subdomain}.localhost"}

        product_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Webhook Widget", "price": "12.00", "stock_qty": 5},
            headers=owner_headers,
        )
        product = product_resp.json()
        await client.post(
            "/api/v1/admin/products/bulk-status",
            json={"product_ids": [product["id"]], "status": "published"},
            headers=owner_headers,
        )

        reg = await client.post(
            "/api/v1/storefront/customers/register",
            json={"email": "webhookbuyer@example.com", "password": "hunter22!!", "name": "Buyer"},
            headers=public_headers,
        )
        customer_headers = {
            **public_headers,
            "Authorization": f"Bearer {reg.json()['access_token']}",
        }
        await client.post(
            "/api/v1/storefront/cart/items",
            json={"product_id": product["id"], "quantity": 1},
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
        order = checkout_resp.json()
        assert order["status"] == "pending"

        # Find the tenant_id the order was created under, from the admin token's claim.
        me_resp = await client.get("/api/v1/admin/me", headers=owner_headers)
        tenant_id = me_resp.json()["tenant_id"]

        fake_gateway.webhook_event = WebhookEvent(
            id="evt_e2e_replay",
            type="checkout.session.completed",
            data={
                "metadata": {
                    "tenant_id": tenant_id,
                    "order_id": order["id"],
                    "kind": "order_payment",
                }
            },
        )

        first_webhook_resp = await client.post(
            "/api/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "valid-signature"},
        )
        assert first_webhook_resp.status_code == 200
        assert first_webhook_resp.json()["status"] == "processed"

        paid_order_resp = await client.get(
            f"/api/v1/admin/orders/{order['id']}", headers=owner_headers
        )
        assert paid_order_resp.json()["status"] == "paid"

        # Replay the exact same webhook delivery a second time.
        second_webhook_resp = await client.post(
            "/api/v1/webhooks/stripe",
            content=b"{}",
            headers={"stripe-signature": "valid-signature"},
        )
        assert second_webhook_resp.status_code == 200
        assert second_webhook_resp.json()["status"] == "already_processed"

        still_paid_order_resp = await client.get(
            f"/api/v1/admin/orders/{order['id']}", headers=owner_headers
        )
        assert still_paid_order_resp.json()["status"] == "paid"
