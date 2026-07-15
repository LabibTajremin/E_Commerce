from uuid import UUID

from src.domain.entities.tenant import Tenant
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.tenant_repository import TenantRepository


class SuspendTenantUseCase:
    def __init__(self, tenant_repository: TenantRepository) -> None:
        self._tenants = tenant_repository

    async def execute(self, tenant_id: UUID) -> Tenant:
        tenant = await self._tenants.get_by_id(tenant_id)
        if tenant is None:
            raise EntityNotFoundError("Tenant", tenant_id)
        tenant.suspend()
        return await self._tenants.update(tenant)


class ReactivateTenantUseCase:
    def __init__(self, tenant_repository: TenantRepository) -> None:
        self._tenants = tenant_repository

    async def execute(self, tenant_id: UUID) -> Tenant:
        tenant = await self._tenants.get_by_id(tenant_id)
        if tenant is None:
            raise EntityNotFoundError("Tenant", tenant_id)
        tenant.reactivate()
        return await self._tenants.update(tenant)
