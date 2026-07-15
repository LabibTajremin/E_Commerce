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


async def _register(client: httpx.AsyncClient, subdomain: str) -> dict:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "tenant_name": subdomain,
            "subdomain": subdomain,
            "owner_email": f"owner@{subdomain}.com",
            "owner_password": "hunter22!!",
        },
        headers={"host": "platform.localhost"},
    )
    assert response.status_code == 201, response.text
    return response.json()


async def test_register_then_login_then_access_me(app, db_session: AsyncSession) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        registered = await _register(client, "e2e-owner-a")

        login_resp = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "owner@e2e-owner-a.com", "password": "hunter22!!"},
            headers={"host": "e2e-owner-a.localhost"},
        )
        assert login_resp.status_code == 200, login_resp.text
        tokens = login_resp.json()

        me_resp = await client.get(
            "/api/v1/admin/me",
            headers={
                "host": "e2e-owner-a.localhost",
                "Authorization": f"Bearer {tokens['access_token']}",
            },
        )
        assert me_resp.status_code == 200
        assert me_resp.json()["tenant_id"] == registered["tenant_id"]


async def test_wrong_password_rejected(app, db_session: AsyncSession) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _register(client, "e2e-owner-b")

        login_resp = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "owner@e2e-owner-b.com", "password": "wrong-password"},
            headers={"host": "e2e-owner-b.localhost"},
        )
        assert login_resp.status_code == 401


async def test_admin_from_tenant_a_cannot_access_tenant_b_scoped_endpoint(
    app, db_session: AsyncSession
) -> None:
    """DoD: cross-tenant auth leakage has an explicit failing-then-passing test."""
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _register(client, "e2e-tenant-a")
        await _register(client, "e2e-tenant-b")

        login_a = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "owner@e2e-tenant-a.com", "password": "hunter22!!"},
            headers={"host": "e2e-tenant-a.localhost"},
        )
        token_a = login_a.json()["access_token"]

        # Same token, but the request resolves to tenant B's subdomain: must be rejected.
        cross_resp = await client.get(
            "/api/v1/admin/me",
            headers={"host": "e2e-tenant-b.localhost", "Authorization": f"Bearer {token_a}"},
        )
        assert cross_resp.status_code == 403

        # Sanity: the same token against its own tenant succeeds.
        own_resp = await client.get(
            "/api/v1/admin/me",
            headers={"host": "e2e-tenant-a.localhost", "Authorization": f"Bearer {token_a}"},
        )
        assert own_resp.status_code == 200


async def test_refresh_and_logout_flow(app, db_session: AsyncSession) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await _register(client, "e2e-owner-c")
        login_resp = await client.post(
            "/api/v1/admin/auth/login",
            json={"email": "owner@e2e-owner-c.com", "password": "hunter22!!"},
            headers={"host": "e2e-owner-c.localhost"},
        )
        tokens = login_resp.json()

        refresh_resp = await client.post(
            "/api/v1/admin/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"host": "e2e-owner-c.localhost"},
        )
        assert refresh_resp.status_code == 200
        new_tokens = refresh_resp.json()
        assert new_tokens["access_token"] != tokens["access_token"]

        # The rotated-out refresh token must now be rejected.
        reuse_resp = await client.post(
            "/api/v1/admin/auth/refresh",
            json={"refresh_token": tokens["refresh_token"]},
            headers={"host": "e2e-owner-c.localhost"},
        )
        assert reuse_resp.status_code == 401

        logout_resp = await client.post(
            "/api/v1/admin/auth/logout",
            json={"refresh_token": new_tokens["refresh_token"]},
            headers={
                "host": "e2e-owner-c.localhost",
                "Authorization": f"Bearer {new_tokens['access_token']}",
            },
        )
        assert logout_resp.status_code == 204

        # The just-revoked access token must no longer work.
        post_logout_resp = await client.get(
            "/api/v1/admin/me",
            headers={
                "host": "e2e-owner-c.localhost",
                "Authorization": f"Bearer {new_tokens['access_token']}",
            },
        )
        assert post_logout_resp.status_code == 401
