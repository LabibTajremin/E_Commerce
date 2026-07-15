from typing import Protocol

from src.domain.entities.master_password_usage import MasterPasswordUsage


class MasterPasswordAuditLogRepository(Protocol):
    async def add(self, usage: MasterPasswordUsage) -> MasterPasswordUsage: ...

    async def list_recent(self, limit: int = 100) -> list[MasterPasswordUsage]: ...
