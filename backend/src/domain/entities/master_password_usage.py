from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class MasterPasswordUsage:
    """One audit record for a successful master-password login — see
    docs/decisions/master-password.md. Global (no tenant_id-scoped RLS),
    same as PlatformAdmin, since a single use can span any tenant."""

    account_type: str  # "admin_user" | "customer" | "platform_admin"
    account_id: UUID
    account_email: str
    ip_address: str
    tenant_id: UUID | None = None
    id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=lambda: datetime.now(UTC))
