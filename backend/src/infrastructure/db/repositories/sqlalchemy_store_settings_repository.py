from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.store_settings import StoreSettings
from src.domain.value_objects.color_hex import ColorHex
from src.infrastructure.db.models.store_settings import StoreSettingsModel


class SqlAlchemyStoreSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: StoreSettingsModel) -> StoreSettings:
        return StoreSettings(
            id=model.id,
            tenant_id=model.tenant_id,
            theme_id=model.theme_id,
            store_name=model.store_name,
            logo_url=model.logo_url,
            favicon_url=model.favicon_url,
            primary_color=ColorHex(model.primary_color),
            accent_color=ColorHex(model.accent_color),
            font_choice=model.font_choice,
            banner_images=list(model.banner_images),
            announcement_bar_text=model.announcement_bar_text,
            social_links=dict(model.social_links),
            seo_meta=dict(model.seo_meta),
            enabled_sections=dict(model.enabled_sections),
            updated_at=model.updated_at,
        )

    async def get_by_tenant(self, tenant_id: UUID) -> StoreSettings | None:
        result = await self._session.execute(
            select(StoreSettingsModel).where(StoreSettingsModel.tenant_id == tenant_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def upsert(self, store_settings: StoreSettings) -> StoreSettings:
        result = await self._session.execute(
            select(StoreSettingsModel).where(
                StoreSettingsModel.tenant_id == store_settings.tenant_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = StoreSettingsModel(id=store_settings.id, tenant_id=store_settings.tenant_id)
            self._session.add(model)

        model.theme_id = store_settings.theme_id
        model.store_name = store_settings.store_name
        model.logo_url = store_settings.logo_url
        model.favicon_url = store_settings.favicon_url
        model.primary_color = str(store_settings.primary_color)
        model.accent_color = str(store_settings.accent_color)
        model.font_choice = store_settings.font_choice
        model.banner_images = list(store_settings.banner_images)
        model.announcement_bar_text = store_settings.announcement_bar_text
        model.social_links = dict(store_settings.social_links)
        model.seo_meta = dict(store_settings.seo_meta)
        model.enabled_sections = dict(store_settings.enabled_sections)

        await self._session.flush()
        return self._to_entity(model)
