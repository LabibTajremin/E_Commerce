from typing import Protocol
from uuid import UUID

from src.domain.entities.store_settings import StoreSettings


class StoreSettingsRepository(Protocol):
    async def get_by_tenant(self, tenant_id: UUID) -> StoreSettings | None: ...

    async def upsert(self, store_settings: StoreSettings) -> StoreSettings: ...
