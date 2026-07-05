from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from src.domain.value_objects.subdomain import Subdomain


class TenantStatus(StrEnum):
    TRIAL = "trial"
    ACTIVE = "active"
    SUSPENDED = "suspended"


@dataclass(slots=True)
class Tenant:
    name: str
    subdomain: Subdomain
    id: UUID = field(default_factory=uuid4)
    custom_domain: str | None = None
    status: TenantStatus = TenantStatus.TRIAL
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def suspend(self) -> None:
        self.status = TenantStatus.SUSPENDED

    def reactivate(self) -> None:
        self.status = TenantStatus.ACTIVE

    @property
    def is_active(self) -> bool:
        return self.status in (TenantStatus.TRIAL, TenantStatus.ACTIVE)
