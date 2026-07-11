from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from src.domain.entities.master_password_usage import MasterPasswordUsage


class MasterPasswordUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    account_type: str
    account_id: UUID
    account_email: str
    tenant_id: UUID | None
    ip_address: str
    occurred_at: datetime

    @classmethod
    def from_entity(cls, usage: MasterPasswordUsage) -> "MasterPasswordUsageResponse":
        return cls(
            id=usage.id,
            account_type=usage.account_type,
            account_id=usage.account_id,
            account_email=usage.account_email,
            tenant_id=usage.tenant_id,
            ip_address=usage.ip_address,
            occurred_at=usage.occurred_at,
        )
