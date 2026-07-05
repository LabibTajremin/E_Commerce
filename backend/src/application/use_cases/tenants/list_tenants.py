from src.domain.entities.tenant import Tenant
from src.domain.repositories.tenant_repository import TenantFilters, TenantRepository


class ListTenantsUseCase:
    def __init__(self, tenant_repository: TenantRepository) -> None:
        self._tenants = tenant_repository

    async def execute(self, filters: TenantFilters) -> list[Tenant]:
        return await self._tenants.list(filters)
