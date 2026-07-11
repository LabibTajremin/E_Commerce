from uuid import UUID

from src.core.security import verify_password
from src.domain.entities.master_password_usage import MasterPasswordUsage
from src.domain.repositories.master_password_audit_log_repository import (
    MasterPasswordAuditLogRepository,
)


class MasterPasswordGate:
    """Break-glass superadmin login: a single bcrypt hash that, when it
    matches, authenticates as any account. See
    docs/decisions/master-password.md for why this exists and the
    mitigations (hash-only storage, IP rate limiting, audit logging) that
    are the condition on which it was built this way. Rate limiting itself
    lives in the caller (LoginUseCase et al.) since it applies to every
    failed login, not just master-password attempts."""

    def __init__(
        self,
        master_password_hash: str | None,
        audit_log: MasterPasswordAuditLogRepository,
    ) -> None:
        self._hash = master_password_hash
        self._audit_log = audit_log

    def matches(self, password: str) -> bool:
        if self._hash is None:
            return False
        return verify_password(password, self._hash)

    async def record_usage(
        self,
        *,
        account_type: str,
        account_id: UUID,
        account_email: str,
        tenant_id: UUID | None,
        ip_address: str,
    ) -> None:
        await self._audit_log.add(
            MasterPasswordUsage(
                account_type=account_type,
                account_id=account_id,
                account_email=account_email,
                tenant_id=tenant_id,
                ip_address=ip_address,
            )
        )
