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


async def _register_and_login(client: httpx.AsyncClient, subdomain: str) -> str:
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


async def test_full_product_crud_flow(app, db_session: AsyncSession) -> None:
    subdomain = "e2e-catalog-a"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_login(client, subdomain)
        headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {token}"}

        category_resp = await client.post(
            "/api/v1/admin/categories", json={"name": "Gadgets"}, headers=headers
        )
        assert category_resp.status_code == 201
        category_id = category_resp.json()["id"]

        create_resp = await client.post(
            "/api/v1/admin/products",
            json={
                "name": "Wireless Mouse",
                "price": "29.99",
                "category_id": category_id,
                "stock_qty": 10,
            },
            headers=headers,
        )
        assert create_resp.status_code == 201
        product = create_resp.json()
        assert product["slug"] == "wireless-mouse"
        assert product["status"] == "draft"

        update_resp = await client.patch(
            f"/api/v1/admin/products/{product['id']}",
            json={"price": "24.99"},
            headers=headers,
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["price"] == "24.99"

        stock_resp = await client.post(
            f"/api/v1/admin/products/{product['id']}/stock",
            json={"delta": -3},
            headers=headers,
        )
        assert stock_resp.status_code == 200
        assert stock_resp.json()["stock_qty"] == 7

        bulk_resp = await client.post(
            "/api/v1/admin/products/bulk-status",
            json={"product_ids": [product["id"]], "status": "published"},
            headers=headers,
        )
        assert bulk_resp.status_code == 200
        assert bulk_resp.json()["updated"] == 1

        list_resp = await client.get(
            "/api/v1/admin/products", params={"status": "published"}, headers=headers
        )
        assert list_resp.status_code == 200
        assert list_resp.json()["total"] == 1

        delete_resp = await client.delete(
            f"/api/v1/admin/products/{product['id']}", headers=headers
        )
        assert delete_resp.status_code == 204

        get_resp = await client.get(f"/api/v1/admin/products/{product['id']}", headers=headers)
        assert get_resp.status_code == 404


async def test_duplicate_sku_within_tenant_returns_409(app, db_session: AsyncSession) -> None:
    subdomain = "e2e-catalog-b"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_login(client, subdomain)
        headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {token}"}

        await client.post(
            "/api/v1/admin/products",
            json={"name": "A", "price": "1.00", "sku": "DUP-1"},
            headers=headers,
        )
        second_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "B", "price": "2.00", "sku": "dup-1"},
            headers=headers,
        )

        assert second_resp.status_code == 409


async def test_tenant_a_cannot_read_tenant_bs_products(app, db_session: AsyncSession) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = await _register_and_login(client, "e2e-catalog-iso-a")
        token_b = await _register_and_login(client, "e2e-catalog-iso-b")

        create_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Tenant B Secret Product", "price": "1.00"},
            headers={
                "host": "e2e-catalog-iso-b.localhost",
                "Authorization": f"Bearer {token_b}",
            },
        )
        product_id = create_resp.json()["id"]

        # Tenant A's token against tenant A's own subdomain, trying tenant B's product id.
        cross_get = await client.get(
            f"/api/v1/admin/products/{product_id}",
            headers={
                "host": "e2e-catalog-iso-a.localhost",
                "Authorization": f"Bearer {token_a}",
            },
        )
        assert cross_get.status_code == 404

        list_resp = await client.get(
            "/api/v1/admin/products",
            headers={
                "host": "e2e-catalog-iso-a.localhost",
                "Authorization": f"Bearer {token_a}",
            },
        )
        assert list_resp.json()["total"] == 0
