from uuid import UUID

from src.domain.entities.tenant import Tenant
from src.domain.repositories.tenant_repository import TenantFilters


class FakeTenantRepository:
    def __init__(self) -> None:
        self._tenants: dict[UUID, Tenant] = {}

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        return self._tenants.get(tenant_id)

    async def get_by_subdomain(self, subdomain: str) -> Tenant | None:
        return next((t for t in self._tenants.values() if str(t.subdomain) == subdomain), None)

    async def get_by_custom_domain(self, custom_domain: str) -> Tenant | None:
        return next(
            (t for t in self._tenants.values() if t.custom_domain == custom_domain), None
        )

    async def list(self, filters: TenantFilters) -> list[Tenant]:
        tenants = list(self._tenants.values())
        if filters.status is not None:
            tenants = [t for t in tenants if t.status == filters.status]
        if filters.search:
            needle = filters.search.lower()
            tenants = [
                t
                for t in tenants
                if needle in t.name.lower() or needle in str(t.subdomain).lower()
            ]
        return tenants[filters.offset : filters.offset + filters.limit]

    async def add(self, tenant: Tenant) -> Tenant:
        self._tenants[tenant.id] = tenant
        return tenant

    async def update(self, tenant: Tenant) -> Tenant:
        self._tenants[tenant.id] = tenant
        return tenant
