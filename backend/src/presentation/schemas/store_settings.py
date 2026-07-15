from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from src.domain.entities.store_settings import StoreSettings
from src.domain.entities.theme import Theme, ThemeLayoutType


class ThemeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    layout_type: ThemeLayoutType
    sections: dict[str, bool]

    @classmethod
    def from_entity(cls, theme: Theme) -> "ThemeResponse":
        return cls(
            id=theme.id, name=theme.name, layout_type=theme.layout_type, sections=theme.sections
        )


class StoreSettingsResponse(BaseModel):
    tenant_id: UUID
    theme_id: UUID
    store_name: str
    logo_url: str | None
    favicon_url: str | None
    primary_color: str
    accent_color: str
    font_choice: str
    banner_images: list[str]
    announcement_bar_text: str | None
    social_links: dict[str, str]
    seo_meta: dict[str, str]
    enabled_sections: dict[str, bool]

    @classmethod
    def from_entity(cls, settings: StoreSettings) -> "StoreSettingsResponse":
        return cls(
            tenant_id=settings.tenant_id,
            theme_id=settings.theme_id,
            store_name=settings.store_name,
            logo_url=settings.logo_url,
            favicon_url=settings.favicon_url,
            primary_color=str(settings.primary_color),
            accent_color=str(settings.accent_color),
            font_choice=settings.font_choice,
            banner_images=settings.banner_images,
            announcement_bar_text=settings.announcement_bar_text,
            social_links=settings.social_links,
            seo_meta=settings.seo_meta,
            enabled_sections=settings.enabled_sections,
        )


class UpdateBrandingRequest(BaseModel):
    store_name: str | None = Field(default=None, max_length=255)
    primary_color: str | None = None
    accent_color: str | None = None
    font_choice: str | None = Field(default=None, max_length=100)
    announcement_bar_text: str | None = Field(default=None, max_length=500)
    social_links: dict[str, str] | None = None
    seo_meta: dict[str, str] | None = None


class SelectThemeRequest(BaseModel):
    theme_id: UUID


class ToggleSectionRequest(BaseModel):
    enabled: bool
