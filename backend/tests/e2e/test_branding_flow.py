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


async def test_full_branding_update_round_trips(app, db_session: AsyncSession) -> None:
    """DoD: an admin can fully theme a store via API and GET it back reflecting
    all changes; malformed input is rejected with a clear 422."""
    subdomain = "e2e-brand-a"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_login(client, subdomain)
        headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {token}"}

        initial = await client.get("/api/v1/admin/store-settings", headers=headers)
        assert initial.status_code == 200
        assert initial.json()["store_name"] == ""

        themes_resp = await client.get("/api/v1/admin/themes", headers=headers)
        assert themes_resp.status_code == 200
        themes = themes_resp.json()
        assert len(themes) >= 3
        minimal_theme = next(t for t in themes if t["name"] == "Minimal")

        update_resp = await client.patch(
            "/api/v1/admin/store-settings",
            json={
                "store_name": "Acme Storefront",
                "primary_color": "#123456",
                "announcement_bar_text": "Free shipping this week!",
            },
            headers=headers,
        )
        assert update_resp.status_code == 200
        body = update_resp.json()
        assert body["store_name"] == "Acme Storefront"
        assert body["primary_color"] == "#123456"

        theme_resp = await client.post(
            "/api/v1/admin/store-settings/theme",
            json={"theme_id": minimal_theme["id"]},
            headers=headers,
        )
        assert theme_resp.status_code == 200
        assert theme_resp.json()["theme_id"] == minimal_theme["id"]
        assert theme_resp.json()["enabled_sections"] == minimal_theme["sections"]

        toggle_resp = await client.patch(
            "/api/v1/admin/store-settings/sections/testimonials",
            json={"enabled": True},
            headers=headers,
        )
        assert toggle_resp.status_code == 200
        assert toggle_resp.json()["enabled_sections"]["testimonials"] is True

        final = await client.get("/api/v1/admin/store-settings", headers=headers)
        final_body = final.json()
        assert final_body["store_name"] == "Acme Storefront"
        assert final_body["announcement_bar_text"] == "Free shipping this week!"
        assert final_body["theme_id"] == minimal_theme["id"]
        assert final_body["enabled_sections"]["testimonials"] is True


async def test_malformed_color_rejected_with_422(app, db_session: AsyncSession) -> None:
    subdomain = "e2e-brand-b"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_login(client, subdomain)
        headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {token}"}

        resp = await client.patch(
            "/api/v1/admin/store-settings",
            json={"primary_color": "not-a-color"},
            headers=headers,
        )

        assert resp.status_code == 422


async def test_selecting_unknown_theme_returns_404(app, db_session: AsyncSession) -> None:
    subdomain = "e2e-brand-c"
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token = await _register_and_login(client, subdomain)
        headers = {"host": f"{subdomain}.localhost", "Authorization": f"Bearer {token}"}

        resp = await client.post(
            "/api/v1/admin/store-settings/theme",
            json={"theme_id": "00000000-0000-0000-0000-000000000099"},
            headers=headers,
        )

        assert resp.status_code == 404


async def test_tenant_a_cannot_see_or_modify_tenant_bs_branding(
    app, db_session: AsyncSession
) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        token_a = await _register_and_login(client, "e2e-brand-iso-a")
        await _register_and_login(client, "e2e-brand-iso-b")

        await client.patch(
            "/api/v1/admin/store-settings",
            json={"store_name": "Tenant A Store"},
            headers={
                "host": "e2e-brand-iso-a.localhost",
                "Authorization": f"Bearer {token_a}",
            },
        )

        # Tenant A's token used against tenant B's subdomain must be rejected outright.
        cross_resp = await client.get(
            "/api/v1/admin/store-settings",
            headers={
                "host": "e2e-brand-iso-b.localhost",
                "Authorization": f"Bearer {token_a}",
            },
        )
        assert cross_resp.status_code == 403
