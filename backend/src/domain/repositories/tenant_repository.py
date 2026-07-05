from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.domain.entities.tenant import Tenant, TenantStatus


@dataclass(frozen=True, slots=True)
class TenantFilters:
    status: TenantStatus | None = None
    search: str | None = None
    limit: int = 50
    offset: int = 0


class TenantRepository(Protocol):
    async def get_by_id(self, tenant_id: UUID) -> Tenant | None: ...

    async def get_by_subdomain(self, subdomain: str) -> Tenant | None: ...

    async def get_by_custom_domain(self, custom_domain: str) -> Tenant | None: ...

    async def list(self, filters: TenantFilters) -> list[Tenant]: ...

    async def add(self, tenant: Tenant) -> Tenant: ...

    async def update(self, tenant: Tenant) -> Tenant: ...
