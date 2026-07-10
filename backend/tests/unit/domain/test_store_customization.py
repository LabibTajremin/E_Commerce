from uuid import uuid4

import pytest

from src.domain.entities.store_settings import MAX_BANNER_IMAGES, StoreSettings
from src.domain.entities.theme import DEFAULT_THEME_SECTIONS, Theme, ThemeLayoutType
from src.domain.exceptions import PlanLimitExceededError
from src.domain.value_objects.color_hex import ColorHex


@pytest.mark.parametrize("invalid", ["", "111111", "#12", "#gggggg", "111"])
def test_invalid_hex_color_rejected(invalid: str) -> None:
    with pytest.raises(ValueError):
        ColorHex(invalid)


@pytest.mark.parametrize("valid", ["#fff", "#FFFFFF", "#111827", "#abc"])
def test_valid_hex_color_accepted_and_normalized_lowercase(valid: str) -> None:
    assert str(ColorHex(valid)) == valid.lower()


def test_new_theme_gets_default_sections() -> None:
    theme = Theme(name="Grid", layout_type=ThemeLayoutType.GRID)
    assert theme.sections == DEFAULT_THEME_SECTIONS


def test_store_settings_add_banner_appends() -> None:
    settings = StoreSettings(tenant_id=uuid4(), theme_id=uuid4())
    settings.add_banner("https://cdn.example.com/a.png")
    assert settings.banner_images == ["https://cdn.example.com/a.png"]


def test_store_settings_add_banner_enforces_plan_limit() -> None:
    settings = StoreSettings(tenant_id=uuid4(), theme_id=uuid4())
    for i in range(MAX_BANNER_IMAGES):
        settings.add_banner(f"https://cdn.example.com/{i}.png")

    with pytest.raises(PlanLimitExceededError):
        settings.add_banner("https://cdn.example.com/one-too-many.png")


def test_store_settings_toggle_section() -> None:
    settings = StoreSettings(tenant_id=uuid4(), theme_id=uuid4())
    settings.toggle_section("testimonials", True)
    assert settings.enabled_sections["testimonials"] is True
