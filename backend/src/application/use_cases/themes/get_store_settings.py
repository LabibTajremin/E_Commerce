from uuid import UUID

from src.domain.entities.store_settings import StoreSettings
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.store_settings_repository import StoreSettingsRepository
from src.domain.repositories.theme_repository import ThemeRepository


class GetStoreSettingsUseCase:
    def __init__(
        self, store_settings_repository: StoreSettingsRepository, theme_repository: ThemeRepository
    ) -> None:
        self._store_settings = store_settings_repository
        self._themes = theme_repository

    async def execute(self, tenant_id: UUID) -> StoreSettings:
        existing = await self._store_settings.get_by_tenant(tenant_id)
        if existing is not None:
            return existing

        themes = await self._themes.list()
        if not themes:
            raise EntityNotFoundError("Theme", "no themes available to default to")

        default_settings = StoreSettings(tenant_id=tenant_id, theme_id=themes[0].id)
        return await self._store_settings.upsert(default_settings)
