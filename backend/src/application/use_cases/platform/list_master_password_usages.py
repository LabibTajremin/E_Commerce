from src.domain.entities.master_password_usage import MasterPasswordUsage
from src.domain.repositories.master_password_audit_log_repository import (
    MasterPasswordAuditLogRepository,
)


class ListMasterPasswordUsagesUseCase:
    def __init__(self, audit_log: MasterPasswordAuditLogRepository) -> None:
        self._audit_log = audit_log

    async def execute(self, limit: int = 100) -> list[MasterPasswordUsage]:
        return await self._audit_log.list_recent(limit)
