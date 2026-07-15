from dataclasses import dataclass
from uuid import UUID

from src.application.use_cases.themes.get_store_settings import GetStoreSettingsUseCase
from src.domain.entities.store_settings import StoreSettings
from src.domain.repositories.store_settings_repository import StoreSettingsRepository
from src.domain.value_objects.color_hex import ColorHex


@dataclass(frozen=True, slots=True)
class UpdateBrandingInput:
    tenant_id: UUID
    store_name: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None
    font_choice: str | None = None
    announcement_bar_text: str | None = None
    social_links: dict[str, str] | None = None
    seo_meta: dict[str, str] | None = None


class UpdateBrandingUseCase:
    def __init__(
        self,
        store_settings_repository: StoreSettingsRepository,
        get_store_settings: GetStoreSettingsUseCase,
    ) -> None:
        self._store_settings = store_settings_repository
        self._get_store_settings = get_store_settings

    async def execute(self, data: UpdateBrandingInput) -> StoreSettings:
        settings = await self._get_store_settings.execute(data.tenant_id)

        if data.store_name is not None:
            settings.store_name = data.store_name
        if data.primary_color is not None:
            settings.primary_color = ColorHex(data.primary_color)
        if data.accent_color is not None:
            settings.accent_color = ColorHex(data.accent_color)
        if data.font_choice is not None:
            settings.font_choice = data.font_choice
        if data.announcement_bar_text is not None:
            settings.announcement_bar_text = data.announcement_bar_text
        if data.social_links is not None:
            settings.social_links = data.social_links
        if data.seo_meta is not None:
            settings.seo_meta = data.seo_meta

        return await self._store_settings.upsert(settings)
