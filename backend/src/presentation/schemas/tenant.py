from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.entities.tenant import Tenant, TenantStatus


class TenantCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    subdomain: str = Field(min_length=1, max_length=63)
    custom_domain: str | None = Field(default=None, max_length=255)


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    subdomain: str
    custom_domain: str | None
    status: TenantStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, tenant: Tenant) -> "TenantResponse":
        return cls(
            id=tenant.id,
            name=tenant.name,
            subdomain=str(tenant.subdomain),
            custom_domain=tenant.custom_domain,
            status=tenant.status,
            created_at=tenant.created_at,
        )
