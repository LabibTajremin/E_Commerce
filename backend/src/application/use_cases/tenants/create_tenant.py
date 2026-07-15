from dataclasses import dataclass

from src.domain.entities.tenant import Tenant
from src.domain.exceptions import EntityAlreadyExistsError
from src.domain.repositories.tenant_repository import TenantRepository
from src.domain.value_objects.subdomain import Subdomain


@dataclass(frozen=True, slots=True)
class CreateTenantInput:
    name: str
    subdomain: str
    custom_domain: str | None = None


class CreateTenantUseCase:
    def __init__(self, tenant_repository: TenantRepository) -> None:
        self._tenants = tenant_repository

    async def execute(self, data: CreateTenantInput) -> Tenant:
        subdomain = Subdomain(data.subdomain)
        existing = await self._tenants.get_by_subdomain(str(subdomain))
        if existing is not None:
            raise EntityAlreadyExistsError("Tenant", str(subdomain))

        tenant = Tenant(name=data.name, subdomain=subdomain, custom_domain=data.custom_domain)
        return await self._tenants.add(tenant)
