import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.tenant import Tenant, TenantStatus
from src.domain.repositories.tenant_repository import TenantFilters
from src.domain.value_objects.subdomain import Subdomain
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)


async def test_add_and_get_by_subdomain(db_session: AsyncSession) -> None:
    repo = SqlAlchemyTenantRepository(db_session)
    tenant = Tenant(name="Acme", subdomain=Subdomain("acme-test"))

    await repo.add(tenant)
    await db_session.commit()

    found = await repo.get_by_subdomain("acme-test")
    assert found is not None
    assert found.id == tenant.id
    assert found.name == "Acme"


async def test_get_by_subdomain_is_isolated_per_tenant(db_session: AsyncSession) -> None:
    repo = SqlAlchemyTenantRepository(db_session)
    tenant_a = Tenant(name="Tenant A", subdomain=Subdomain("tenant-a"))
    tenant_b = Tenant(name="Tenant B", subdomain=Subdomain("tenant-b"))

    await repo.add(tenant_a)
    await repo.add(tenant_b)
    await db_session.commit()

    found_a = await repo.get_by_subdomain("tenant-a")
    found_b = await repo.get_by_subdomain("tenant-b")

    assert found_a is not None and found_a.id == tenant_a.id
    assert found_b is not None and found_b.id == tenant_b.id
    assert found_a.id != found_b.id


async def test_duplicate_subdomain_violates_unique_constraint(db_session: AsyncSession) -> None:
    repo = SqlAlchemyTenantRepository(db_session)
    await repo.add(Tenant(name="First", subdomain=Subdomain("dup-slug")))
    await db_session.commit()

    with pytest.raises(Exception):  # noqa: PT011, B017
        await repo.add(Tenant(name="Second", subdomain=Subdomain("dup-slug")))
        await db_session.commit()


async def test_list_filters_by_status(db_session: AsyncSession) -> None:
    repo = SqlAlchemyTenantRepository(db_session)
    active = Tenant(name="Active Co", subdomain=Subdomain("active-co"), status=TenantStatus.ACTIVE)
    suspended = Tenant(
        name="Suspended Co", subdomain=Subdomain("suspended-co"), status=TenantStatus.SUSPENDED
    )
    await repo.add(active)
    await repo.add(suspended)
    await db_session.commit()

    results = await repo.list(TenantFilters(status=TenantStatus.SUSPENDED))

    ids = {t.id for t in results}
    assert suspended.id in ids
    assert active.id not in ids
