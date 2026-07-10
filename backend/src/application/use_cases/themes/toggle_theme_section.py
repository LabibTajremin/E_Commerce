from dataclasses import dataclass
from uuid import UUID

from src.application.use_cases.themes.get_store_settings import GetStoreSettingsUseCase
from src.domain.entities.store_settings import StoreSettings
from src.domain.repositories.store_settings_repository import StoreSettingsRepository


@dataclass(frozen=True, slots=True)
class ToggleThemeSectionInput:
    tenant_id: UUID
    section: str
    enabled: bool


class ToggleThemeSectionUseCase:
    def __init__(
        self,
        store_settings_repository: StoreSettingsRepository,
        get_store_settings: GetStoreSettingsUseCase,
    ) -> None:
        self._store_settings = store_settings_repository
        self._get_store_settings = get_store_settings

    async def execute(self, data: ToggleThemeSectionInput) -> StoreSettings:
        settings = await self._get_store_settings.execute(data.tenant_id)
        settings.toggle_section(data.section, data.enabled)
        return await self._store_settings.upsert(settings)
