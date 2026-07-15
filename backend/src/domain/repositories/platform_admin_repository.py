from typing import Protocol
from uuid import UUID

from src.domain.entities.platform_admin import PlatformAdmin


class PlatformAdminRepository(Protocol):
    async def get_by_id(self, platform_admin_id: UUID) -> PlatformAdmin | None: ...

    async def get_by_email(self, email: str) -> PlatformAdmin | None: ...

    async def add(self, platform_admin: PlatformAdmin) -> PlatformAdmin: ...
