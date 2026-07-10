from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TokenPair:
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


@dataclass(frozen=True, slots=True)
class AuthenticatedAdmin:
    user_id: UUID
    tenant_id: UUID
    role: str
