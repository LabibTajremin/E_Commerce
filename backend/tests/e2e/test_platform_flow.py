from decimal import Decimal

import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.security import hash_password
from src.domain.entities.platform_admin import PlatformAdmin
from src.domain.value_objects.email import Email
from src.infrastructure.db.models.subscription_plan import SubscriptionPlanModel
from src.infrastructure.db.repositories.sqlalchemy_platform_admin_repository import (
    SqlAlchemyPlatformAdminRepository,
)


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


async def _seed_platform_admin(db_session: AsyncSession, email: str, password: str) -> None:
    repo = SqlAlchemyPlatformAdminRepository(db_session)
    await repo.add(PlatformAdmin(email=Email(email), hashed_password=hash_password(password)))
    await db_session.commit()


async def _login_platform_admin(client: httpx.AsyncClient, email: str, password: str) -> str:
    resp = await client.post(
        "/api/v1/platform/auth/login",
        json={"email": email, "password": password},
        headers={"host": "platform.localhost"},
    )
    assert resp.status_code == 200, resp.text
    return str(resp.json()["access_token"])


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


async def test_platform_admin_login_rejects_wrong_password(
    app, db_session: AsyncSession
) -> None:
    await _seed_platform_admin(db_session, "root-a@platform.com", "hunter22!!")
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/platform/auth/login",
            json={"email": "root-a@platform.com", "password": "wrong"},
            headers={"host": "platform.localhost"},
        )
        assert resp.status_code == 401


async def test_tenant_endpoints_require_platform_admin_token(
    app, db_session: AsyncSession
) -> None:
    await _seed_platform_admin(db_session, "root-b@platform.com", "hunter22!!")
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        no_auth_resp = await client.get(
            "/api/v1/platform/tenants", headers={"host": "platform.localhost"}
        )
        assert no_auth_resp.status_code == 401

        token = await _login_platform_admin(client, "root-b@platform.com", "hunter22!!")
        auth_resp = await client.get(
            "/api/v1/platform/tenants",
            headers={"host": "platform.localhost", "Authorization": f"Bearer {token}"},
        )
        assert auth_resp.status_code == 200

        # A tenant-scoped admin token must not pass the superadmin gate.
        tenant_token = await _register_and_login_owner(client, "e2e-plat-cross")
        cross_resp = await client.get(
            "/api/v1/platform/tenants",
            headers={"host": "platform.localhost", "Authorization": f"Bearer {tenant_token}"},
        )
        assert cross_resp.status_code == 403


async def test_tenant_usage_and_plan_override_flow(app, db_session: AsyncSession) -> None:
    await _seed_platform_admin(db_session, "root-c@platform.com", "hunter22!!")
    starter = SubscriptionPlanModel(
        name="E2E Starter",
        price=Decimal("0"),
        max_products=1,
        max_banners=1,
        custom_domain_allowed=False,
    )
    growth = SubscriptionPlanModel(
        name="E2E Growth",
        price=Decimal("29"),
        max_products=100,
        max_banners=10,
        custom_domain_allowed=False,
    )
    db_session.add_all([starter, growth])
    await db_session.flush()
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await _register_and_login_owner(client, "e2e-plat-usage")
        me_resp = await client.get(
            "/api/v1/admin/me",
            headers={"host": "e2e-plat-usage.localhost", "Authorization": f"Bearer {owner_token}"},
        )
        tenant_id = me_resp.json()["tenant_id"]

        admin_token = await _login_platform_admin(client, "root-c@platform.com", "hunter22!!")
        admin_headers = {"host": "platform.localhost", "Authorization": f"Bearer {admin_token}"}

        override_resp = await client.post(
            f"/api/v1/platform/tenants/{tenant_id}/plan-override",
            json={"plan_id": str(starter.id)},
            headers=admin_headers,
        )
        assert override_resp.status_code == 200, override_resp.text
        assert override_resp.json()["plan_id"] == str(starter.id)

        usage_resp = await client.get(
            f"/api/v1/platform/tenants/{tenant_id}/usage", headers=admin_headers
        )
        assert usage_resp.status_code == 200, usage_resp.text
        usage = usage_resp.json()
        assert usage["plan"]["id"] == str(starter.id)
        assert usage["product_count"] == 0

        # Move the tenant to a roomier plan and confirm the usage view reflects it.
        await client.post(
            f"/api/v1/platform/tenants/{tenant_id}/plan-override",
            json={"plan_id": str(growth.id)},
            headers=admin_headers,
        )
        usage_resp_2 = await client.get(
            f"/api/v1/platform/tenants/{tenant_id}/usage", headers=admin_headers
        )
        assert usage_resp_2.json()["plan"]["id"] == str(growth.id)


async def test_suspended_tenant_immediately_blocks_admin_api_access(
    app, db_session: AsyncSession
) -> None:
    await _seed_platform_admin(db_session, "root-d@platform.com", "hunter22!!")
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        owner_token = await _register_and_login_owner(client, "e2e-plat-suspend")
        owner_headers = {
            "host": "e2e-plat-suspend.localhost",
            "Authorization": f"Bearer {owner_token}",
        }

        me_resp = await client.get("/api/v1/admin/me", headers=owner_headers)
        assert me_resp.status_code == 200
        tenant_id = me_resp.json()["tenant_id"]

        admin_token = await _login_platform_admin(client, "root-d@platform.com", "hunter22!!")
        admin_headers = {"host": "platform.localhost", "Authorization": f"Bearer {admin_token}"}

        suspend_resp = await client.post(
            f"/api/v1/platform/tenants/{tenant_id}/suspend", headers=admin_headers
        )
        assert suspend_resp.status_code == 200
        assert suspend_resp.json()["status"] == "suspended"

        blocked_resp = await client.get("/api/v1/admin/me", headers=owner_headers)
        assert blocked_resp.status_code == 404

        reactivate_resp = await client.post(
            f"/api/v1/platform/tenants/{tenant_id}/reactivate", headers=admin_headers
        )
        assert reactivate_resp.status_code == 200

        restored_resp = await client.get("/api/v1/admin/me", headers=owner_headers)
        assert restored_resp.status_code == 200
