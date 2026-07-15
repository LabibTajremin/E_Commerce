from dataclasses import dataclass
from uuid import UUID

from src.application.use_cases.themes.get_store_settings import GetStoreSettingsUseCase
from src.domain.entities.store_settings import StoreSettings
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.store_settings_repository import StoreSettingsRepository
from src.domain.repositories.theme_repository import ThemeRepository


@dataclass(frozen=True, slots=True)
class SelectThemeInput:
    tenant_id: UUID
    theme_id: UUID


class SelectThemeUseCase:
    def __init__(
        self,
        store_settings_repository: StoreSettingsRepository,
        theme_repository: ThemeRepository,
        get_store_settings: GetStoreSettingsUseCase,
    ) -> None:
        self._store_settings = store_settings_repository
        self._themes = theme_repository
        self._get_store_settings = get_store_settings

    async def execute(self, data: SelectThemeInput) -> StoreSettings:
        theme = await self._themes.get_by_id(data.theme_id)
        if theme is None:
            raise EntityNotFoundError("Theme", data.theme_id)

        settings = await self._get_store_settings.execute(data.tenant_id)
        settings.theme_id = theme.id
        settings.enabled_sections = dict(theme.sections)
        return await self._store_settings.upsert(settings)
