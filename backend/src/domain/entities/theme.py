from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID, uuid4

DEFAULT_THEME_SECTIONS: dict[str, bool] = {
    "hero_banner": True,
    "featured_products": True,
    "testimonials": False,
    "footer": True,
}


class ThemeLayoutType(StrEnum):
    GRID = "grid"
    MINIMAL = "minimal"
    CLASSIC = "classic"


@dataclass(slots=True)
class Theme:
    name: str
    layout_type: ThemeLayoutType
    id: UUID = field(default_factory=uuid4)
    sections: dict[str, bool] = field(default_factory=lambda: dict(DEFAULT_THEME_SECTIONS))
