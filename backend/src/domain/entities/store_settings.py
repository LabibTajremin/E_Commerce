from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.entities.theme import DEFAULT_THEME_SECTIONS
from src.domain.exceptions import PlanLimitExceededError
from src.domain.value_objects.color_hex import ColorHex

MAX_BANNER_IMAGES = 5  # interim constant limit; Phase 8's PlanLimitPolicy replaces this.


@dataclass(slots=True)
class StoreSettings:
    tenant_id: UUID
    theme_id: UUID
    id: UUID = field(default_factory=uuid4)
    store_name: str = ""
    logo_url: str | None = None
    favicon_url: str | None = None
    primary_color: ColorHex = field(default_factory=lambda: ColorHex("#111827"))
    accent_color: ColorHex = field(default_factory=lambda: ColorHex("#2563eb"))
    font_choice: str = "Inter"
    banner_images: list[str] = field(default_factory=list)
    announcement_bar_text: str | None = None
    social_links: dict[str, str] = field(default_factory=dict)
    seo_meta: dict[str, str] = field(default_factory=dict)
    enabled_sections: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_THEME_SECTIONS))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def add_banner(self, url: str) -> None:
        if len(self.banner_images) >= MAX_BANNER_IMAGES:
            raise PlanLimitExceededError(
                f"Banner limit reached ({MAX_BANNER_IMAGES} max for this plan)"
            )
        self.banner_images.append(url)

    def toggle_section(self, section: str, enabled: bool) -> None:
        self.enabled_sections[section] = enabled
