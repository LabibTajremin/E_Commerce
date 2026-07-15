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


async def test_draft_products_never_appear_on_storefront(app, db_session: AsyncSession) -> None:
    subdomain = "e2e-store-a"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_login(client, subdomain)
        admin_headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {token}"}
        public_headers = {"host": f"{subdomain}.localhost"}

        draft_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Secret Draft", "price": "9.99"},
            headers=admin_headers,
        )
        draft = draft_resp.json()

        published_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Visible Product", "price": "19.99"},
            headers=admin_headers,
        )
        published = published_resp.json()
        await client.post(
            "/api/v1/admin/products/bulk-status",
            json={"product_ids": [published["id"]], "status": "published"},
            headers=admin_headers,
        )

        list_resp = await client.get("/api/v1/storefront/products", headers=public_headers)
        assert list_resp.status_code == 200
        items = list_resp.json()["items"]
        assert {p["id"] for p in items} == {published["id"]}

        draft_detail_resp = await client.get(
            f"/api/v1/storefront/products/{draft['slug']}", headers=public_headers
        )
        assert draft_detail_resp.status_code == 404

        published_detail_resp = await client.get(
            f"/api/v1/storefront/products/{published['slug']}", headers=public_headers
        )
        assert published_detail_resp.status_code == 200
        assert "tenant_id" not in published_detail_resp.json()
        assert "sku" not in published_detail_resp.json()


async def test_storefront_cache_busts_on_admin_update(app, db_session: AsyncSession) -> None:
    """DoD: update product -> cache busted -> new data served."""
    subdomain = "e2e-store-b"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_login(client, subdomain)
        admin_headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {token}"}
        public_headers = {"host": f"{subdomain}.localhost"}

        create_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Cacheable Widget", "price": "10.00"},
            headers=admin_headers,
        )
        product = create_resp.json()
        await client.post(
            "/api/v1/admin/products/bulk-status",
            json={"product_ids": [product["id"]], "status": "published"},
            headers=admin_headers,
        )

        first_resp = await client.get(
            f"/api/v1/storefront/products/{product['slug']}", headers=public_headers
        )
        assert first_resp.json()["price"] == "10.00"

        # Still cached: a direct repo write wouldn't reflect here, but we go
        # through the real admin endpoint, which busts the cache version.
        await client.patch(
            f"/api/v1/admin/products/{product['id']}", json={"price": "7.50"}, headers=admin_headers
        )

        second_resp = await client.get(
            f"/api/v1/storefront/products/{product['slug']}", headers=public_headers
        )
        assert second_resp.json()["price"] == "7.50"


async def test_storefront_store_settings_and_categories_are_public(
    app, db_session: AsyncSession
) -> None:
    subdomain = "e2e-store-c"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_login(client, subdomain)
        admin_headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {token}"}
        public_headers = {"host": f"{subdomain}.localhost"}

        await client.post(
            "/api/v1/admin/categories", json={"name": "Gadgets"}, headers=admin_headers
        )
        await client.patch(
            "/api/v1/admin/store-settings",
            json={"store_name": "Acme Public Store"},
            headers=admin_headers,
        )

        categories_resp = await client.get("/api/v1/storefront/categories", headers=public_headers)
        assert categories_resp.status_code == 200
        assert categories_resp.json()["items"][0]["name"] == "Gadgets"

        store_resp = await client.get("/api/v1/storefront/store", headers=public_headers)
        assert store_resp.status_code == 200
        assert store_resp.json()["store_name"] == "Acme Public Store"


async def test_cross_tenant_storefront_isolation(app, db_session: AsyncSession) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = await _register_and_login(client, "e2e-store-iso-a")
        await _register_and_login(client, "e2e-store-iso-b")

        product_resp = await client.post(
            "/api/v1/admin/products",
            json={"name": "Tenant A Product", "price": "1.00"},
            headers={
                "host": "e2e-store-iso-a.localhost",
                "Authorization": f"Bearer {token_a}",
            },
        )
        product = product_resp.json()
        await client.post(
            "/api/v1/admin/products/bulk-status",
            json={"product_ids": [product["id"]], "status": "published"},
            headers={
                "host": "e2e-store-iso-a.localhost",
                "Authorization": f"Bearer {token_a}",
            },
        )

        # Same slug looked up on tenant B's storefront must not find tenant A's product.
        cross_resp = await client.get(
            f"/api/v1/storefront/products/{product['slug']}",
            headers={"host": "e2e-store-iso-b.localhost"},
        )
        assert cross_resp.status_code == 404

        tenant_b_list = await client.get(
            "/api/v1/storefront/products", headers={"host": "e2e-store-iso-b.localhost"}
        )
        assert tenant_b_list.json()["total"] == 0
