import httpx
import pytest
from httpx import ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.tenant import Tenant, TenantStatus
from src.domain.value_objects.subdomain import Subdomain
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)


@pytest.fixture
def app(database_url: str, _run_migrations: None):
    import src.core.config as config_module

    config_module.settings.database_url = database_url
    import src.infrastructure.db.session as session_module

    session_module.engine = session_module.create_engine(database_url)
    session_module.async_session_factory = session_module.async_sessionmaker(
        session_module.engine, expire_on_commit=False, autoflush=False
    )

    from src.main import app as fastapi_app

    return fastapi_app


async def test_unresolvable_subdomain_returns_404(app, db_session: AsyncSession) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/some-path", headers={"host": "ghost.localhost"})
    assert response.status_code == 404


async def test_valid_subdomain_attaches_tenant_context(app, db_session: AsyncSession) -> None:
    repo = SqlAlchemyTenantRepository(db_session)
    tenant = Tenant(
        name="Acme", subdomain=Subdomain("acme-e2e"), status=TenantStatus.ACTIVE
    )
    await repo.add(tenant)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/storefront/context", headers={"host": "acme-e2e.localhost"}
        )

    assert response.status_code == 200
    assert response.json()["tenant_id"] == str(tenant.id)


async def test_two_tenants_resolve_to_distinct_isolated_context(
    app, db_session: AsyncSession
) -> None:
    repo = SqlAlchemyTenantRepository(db_session)
    tenant_a = Tenant(name="A", subdomain=Subdomain("resolve-a"), status=TenantStatus.ACTIVE)
    tenant_b = Tenant(name="B", subdomain=Subdomain("resolve-b"), status=TenantStatus.ACTIVE)
    await repo.add(tenant_a)
    await repo.add(tenant_b)
    await db_session.commit()

    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp_a = await client.get(
            "/api/v1/storefront/context", headers={"host": "resolve-a.localhost"}
        )
        resp_b = await client.get(
            "/api/v1/storefront/context", headers={"host": "resolve-b.localhost"}
        )

    assert resp_a.json()["tenant_id"] == str(tenant_a.id)
    assert resp_b.json()["tenant_id"] == str(tenant_b.id)
    assert resp_a.json()["tenant_id"] != resp_b.json()["tenant_id"]


async def test_platform_routes_exempt_from_tenant_resolution(app) -> None:
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(
            "/api/v1/platform/tenants", headers={"host": "unknown.localhost"}
        )
    assert response.status_code != 404
