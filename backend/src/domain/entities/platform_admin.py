from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.value_objects.email import Email


@dataclass(slots=True)
class PlatformAdmin:
    """A superadmin account that operates across all tenants. Deliberately not
    an AdminUser — it doesn't belong to any tenant and can't be created via
    self-registration, only via the bootstrap script."""

    email: Email
    hashed_password: str
    id: UUID = field(default_factory=uuid4)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
