from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.value_objects.address import Address
from src.domain.value_objects.email import Email


@dataclass(slots=True)
class Customer:
    tenant_id: UUID
    email: Email
    hashed_password: str
    name: str
    id: UUID = field(default_factory=uuid4)
    addresses: list[Address] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
