from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from src.domain.value_objects.email import Email


class AdminRole(StrEnum):
    OWNER = "owner"
    STAFF = "staff"


class AdminUserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


@dataclass(slots=True)
class AdminUser:
    tenant_id: UUID
    email: Email
    hashed_password: str
    id: UUID = field(default_factory=uuid4)
    role: AdminRole = AdminRole.OWNER
    status: AdminUserStatus = AdminUserStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_active(self) -> bool:
        return self.status == AdminUserStatus.ACTIVE

    def disable(self) -> None:
        self.status = AdminUserStatus.DISABLED
