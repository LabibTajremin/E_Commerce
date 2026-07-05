from uuid import uuid4

import pytest

from src.application.use_cases.tenants.create_tenant import (
    CreateTenantInput,
    CreateTenantUseCase,
)
from src.application.use_cases.tenants.list_tenants import ListTenantsUseCase
from src.application.use_cases.tenants.suspend_tenant import (
    ReactivateTenantUseCase,
    SuspendTenantUseCase,
)
from src.domain.entities.tenant import TenantStatus
from src.domain.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from src.domain.repositories.tenant_repository import TenantFilters
from tests.unit.application.fakes import FakeTenantRepository


async def test_create_tenant_succeeds() -> None:
    repo = FakeTenantRepository()
    use_case = CreateTenantUseCase(repo)

    tenant = await use_case.execute(CreateTenantInput(name="Acme", subdomain="acme"))

    assert tenant.name == "Acme"
    assert str(tenant.subdomain) == "acme"
    assert await repo.get_by_subdomain("acme") is not None


async def test_create_tenant_rejects_duplicate_subdomain() -> None:
    repo = FakeTenantRepository()
    use_case = CreateTenantUseCase(repo)
    await use_case.execute(CreateTenantInput(name="Acme", subdomain="acme"))

    with pytest.raises(EntityAlreadyExistsError):
        await use_case.execute(CreateTenantInput(name="Acme Two", subdomain="acme"))


async def test_suspend_tenant_not_found_raises() -> None:
    repo = FakeTenantRepository()
    use_case = SuspendTenantUseCase(repo)

    with pytest.raises(EntityNotFoundError):
        await use_case.execute(uuid4())


async def test_suspend_tenant_updates_status() -> None:
    repo = FakeTenantRepository()
    create_use_case = CreateTenantUseCase(repo)
    tenant = await create_use_case.execute(CreateTenantInput(name="Acme", subdomain="acme"))

    suspend_use_case = SuspendTenantUseCase(repo)
    suspended = await suspend_use_case.execute(tenant.id)

    assert suspended.status == TenantStatus.SUSPENDED


async def test_reactivate_tenant_not_found_raises() -> None:
    repo = FakeTenantRepository()
    use_case = ReactivateTenantUseCase(repo)

    with pytest.raises(EntityNotFoundError):
        await use_case.execute(uuid4())


async def test_reactivate_tenant_restores_active_status() -> None:
    repo = FakeTenantRepository()
    tenant = await CreateTenantUseCase(repo).execute(
        CreateTenantInput(name="Acme", subdomain="acme")
    )
    await SuspendTenantUseCase(repo).execute(tenant.id)

    reactivated = await ReactivateTenantUseCase(repo).execute(tenant.id)

    assert reactivated.status == TenantStatus.ACTIVE


async def test_list_tenants_applies_filters() -> None:
    repo = FakeTenantRepository()
    create_use_case = CreateTenantUseCase(repo)
    await create_use_case.execute(CreateTenantInput(name="Acme", subdomain="acme"))
    await create_use_case.execute(CreateTenantInput(name="Globex", subdomain="globex"))

    results = await ListTenantsUseCase(repo).execute(TenantFilters(search="acme"))

    assert len(results) == 1
    assert results[0].name == "Acme"
