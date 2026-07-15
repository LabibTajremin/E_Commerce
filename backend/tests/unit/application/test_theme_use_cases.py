from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.use_cases.billing.get_effective_plan import GetEffectivePlanUseCase
from src.application.use_cases.themes.get_store_settings import GetStoreSettingsUseCase
from src.application.use_cases.themes.select_theme import SelectThemeInput, SelectThemeUseCase
from src.application.use_cases.themes.toggle_theme_section import (
    ToggleThemeSectionInput,
    ToggleThemeSectionUseCase,
)
from src.application.use_cases.themes.update_branding import (
    UpdateBrandingInput,
    UpdateBrandingUseCase,
)
from src.application.use_cases.themes.upload_store_image import (
    ImageKind,
    UploadStoreImageInput,
    UploadStoreImageUseCase,
)
from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.entities.theme import Theme, ThemeLayoutType
from src.domain.exceptions import EntityNotFoundError, PlanLimitExceededError, ValidationError
from src.domain.value_objects.money import Money
from tests.unit.application.fakes import (
    FakeObjectStorage,
    FakeStoreSettingsRepository,
    FakeSubscriptionPlanRepository,
    FakeTenantSubscriptionRepository,
    FakeThemeRepository,
    unlimited_plan_use_case,
)


def _grid_theme() -> Theme:
    return Theme(name="Grid", layout_type=ThemeLayoutType.GRID)


async def test_get_store_settings_lazily_creates_defaults() -> None:
    theme = _grid_theme()
    themes = FakeThemeRepository([theme])
    store_settings = FakeStoreSettingsRepository()
    tenant_id = uuid4()

    settings = await GetStoreSettingsUseCase(store_settings, themes).execute(tenant_id)

    assert settings.tenant_id == tenant_id
    assert settings.theme_id == theme.id
    assert await store_settings.get_by_tenant(tenant_id) is not None


async def test_get_store_settings_returns_existing_without_recreating() -> None:
    theme = _grid_theme()
    themes = FakeThemeRepository([theme])
    store_settings = FakeStoreSettingsRepository()
    tenant_id = uuid4()
    use_case = GetStoreSettingsUseCase(store_settings, themes)

    first = await use_case.execute(tenant_id)
    first.store_name = "Renamed"
    await store_settings.upsert(first)

    second = await use_case.execute(tenant_id)
    assert second.store_name == "Renamed"


async def test_update_branding_applies_only_provided_fields() -> None:
    theme = _grid_theme()
    themes = FakeThemeRepository([theme])
    store_settings = FakeStoreSettingsRepository()
    tenant_id = uuid4()
    get_use_case = GetStoreSettingsUseCase(store_settings, themes)
    await get_use_case.execute(tenant_id)

    updated = await UpdateBrandingUseCase(store_settings, get_use_case).execute(
        UpdateBrandingInput(tenant_id=tenant_id, store_name="Acme Store", primary_color="#ff0000")
    )

    assert updated.store_name == "Acme Store"
    assert str(updated.primary_color) == "#ff0000"


async def test_select_theme_switches_theme_and_resets_sections() -> None:
    grid = _grid_theme()
    minimal = Theme(
        name="Minimal", layout_type=ThemeLayoutType.MINIMAL, sections={"hero_banner": False}
    )
    themes = FakeThemeRepository([grid, minimal])
    store_settings = FakeStoreSettingsRepository()
    tenant_id = uuid4()
    get_use_case = GetStoreSettingsUseCase(store_settings, themes)
    await get_use_case.execute(tenant_id)

    updated = await SelectThemeUseCase(store_settings, themes, get_use_case).execute(
        SelectThemeInput(tenant_id=tenant_id, theme_id=minimal.id)
    )

    assert updated.theme_id == minimal.id
    assert updated.enabled_sections == {"hero_banner": False}


async def test_select_theme_rejects_unknown_theme() -> None:
    themes = FakeThemeRepository([_grid_theme()])
    store_settings = FakeStoreSettingsRepository()
    get_use_case = GetStoreSettingsUseCase(store_settings, themes)

    with pytest.raises(EntityNotFoundError):
        await SelectThemeUseCase(store_settings, themes, get_use_case).execute(
            SelectThemeInput(tenant_id=uuid4(), theme_id=uuid4())
        )


async def test_toggle_theme_section() -> None:
    themes = FakeThemeRepository([_grid_theme()])
    store_settings = FakeStoreSettingsRepository()
    tenant_id = uuid4()
    get_use_case = GetStoreSettingsUseCase(store_settings, themes)
    await get_use_case.execute(tenant_id)

    updated = await ToggleThemeSectionUseCase(store_settings, get_use_case).execute(
        ToggleThemeSectionInput(tenant_id=tenant_id, section="testimonials", enabled=True)
    )

    assert updated.enabled_sections["testimonials"] is True


async def test_upload_store_image_sets_logo_url() -> None:
    themes = FakeThemeRepository([_grid_theme()])
    store_settings = FakeStoreSettingsRepository()
    storage = FakeObjectStorage()
    tenant_id = uuid4()
    get_use_case = GetStoreSettingsUseCase(store_settings, themes)
    await get_use_case.execute(tenant_id)

    updated = await UploadStoreImageUseCase(
        store_settings, get_use_case, storage, unlimited_plan_use_case()
    ).execute(
        UploadStoreImageInput(
            tenant_id=tenant_id,
            kind=ImageKind.LOGO,
            content=b"fake-png-bytes",
            content_type="image/png",
            filename="logo.png",
        )
    )

    assert updated.logo_url is not None
    assert updated.logo_url.startswith("https://cdn.test/")
    assert len(storage.uploaded) == 1


async def test_upload_store_image_rejects_disallowed_content_type() -> None:
    themes = FakeThemeRepository([_grid_theme()])
    store_settings = FakeStoreSettingsRepository()
    storage = FakeObjectStorage()
    get_use_case = GetStoreSettingsUseCase(store_settings, themes)

    with pytest.raises(ValidationError):
        await UploadStoreImageUseCase(
            store_settings, get_use_case, storage, unlimited_plan_use_case()
        ).execute(
            UploadStoreImageInput(
                tenant_id=uuid4(),
                kind=ImageKind.BANNER,
                content=b"<svg onload=alert(1)>",
                content_type="image/svg+xml",
                filename="evil.svg",
            )
        )


async def test_upload_store_image_rejects_oversized_file() -> None:
    themes = FakeThemeRepository([_grid_theme()])
    store_settings = FakeStoreSettingsRepository()
    storage = FakeObjectStorage()
    get_use_case = GetStoreSettingsUseCase(store_settings, themes)

    with pytest.raises(ValidationError):
        await UploadStoreImageUseCase(
            store_settings, get_use_case, storage, unlimited_plan_use_case()
        ).execute(
            UploadStoreImageInput(
                tenant_id=uuid4(),
                kind=ImageKind.BANNER,
                content=b"0" * (5 * 1024 * 1024 + 1),
                content_type="image/png",
                filename="huge.png",
            )
        )


async def test_upload_store_image_enforces_banner_plan_limit() -> None:
    themes = FakeThemeRepository([_grid_theme()])
    store_settings = FakeStoreSettingsRepository()
    storage = FakeObjectStorage()
    tenant_id = uuid4()
    get_use_case = GetStoreSettingsUseCase(store_settings, themes)
    await get_use_case.execute(tenant_id)

    plan = SubscriptionPlan(
        name="Starter",
        price=Money(Decimal("0")),
        max_products=100,
        max_banners=1,
        custom_domain_allowed=False,
    )
    get_effective_plan = GetEffectivePlanUseCase(
        FakeSubscriptionPlanRepository([plan]), FakeTenantSubscriptionRepository()
    )

    upload_use_case = UploadStoreImageUseCase(
        store_settings, get_use_case, storage, get_effective_plan
    )
    await upload_use_case.execute(
        UploadStoreImageInput(
            tenant_id=tenant_id,
            kind=ImageKind.BANNER,
            content=b"fake-png-bytes",
            content_type="image/png",
            filename="banner-1.png",
        )
    )

    with pytest.raises(PlanLimitExceededError):
        await upload_use_case.execute(
            UploadStoreImageInput(
                tenant_id=tenant_id,
                kind=ImageKind.BANNER,
                content=b"fake-png-bytes-2",
                content_type="image/png",
                filename="banner-2.png",
            )
        )
