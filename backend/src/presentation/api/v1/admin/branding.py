from fastapi import APIRouter, File, Form, UploadFile

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
from src.presentation.caching import storefront_cache_namespace
from src.presentation.dependencies import (
    CacheDep,
    CurrentAdminDep,
    GetEffectivePlanUseCaseDep,
    GetStoreSettingsUseCaseDep,
    ObjectStorageDep,
    StoreSettingsRepositoryDep,
    ThemeRepositoryDep,
)
from src.presentation.schemas.store_settings import (
    SelectThemeRequest,
    StoreSettingsResponse,
    ThemeResponse,
    ToggleSectionRequest,
    UpdateBrandingRequest,
)

router = APIRouter(tags=["admin:branding"])


@router.get("/themes", response_model=list[ThemeResponse])
async def list_themes(
    current: CurrentAdminDep, theme_repository: ThemeRepositoryDep
) -> list[ThemeResponse]:
    del current
    themes = await theme_repository.list()
    return [ThemeResponse.from_entity(t) for t in themes]


@router.get("/store-settings", response_model=StoreSettingsResponse)
async def get_store_settings(
    current: CurrentAdminDep, get_store_settings_uc: GetStoreSettingsUseCaseDep
) -> StoreSettingsResponse:
    settings = await get_store_settings_uc.execute(current.tenant_id)
    return StoreSettingsResponse.from_entity(settings)


@router.patch("/store-settings", response_model=StoreSettingsResponse)
async def update_branding(
    body: UpdateBrandingRequest,
    current: CurrentAdminDep,
    store_settings_repository: StoreSettingsRepositoryDep,
    get_store_settings_uc: GetStoreSettingsUseCaseDep,
    cache: CacheDep,
) -> StoreSettingsResponse:
    use_case = UpdateBrandingUseCase(store_settings_repository, get_store_settings_uc)
    settings = await use_case.execute(
        UpdateBrandingInput(tenant_id=current.tenant_id, **body.model_dump(exclude_unset=True))
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return StoreSettingsResponse.from_entity(settings)


@router.post("/store-settings/theme", response_model=StoreSettingsResponse)
async def select_theme(
    body: SelectThemeRequest,
    current: CurrentAdminDep,
    store_settings_repository: StoreSettingsRepositoryDep,
    theme_repository: ThemeRepositoryDep,
    get_store_settings_uc: GetStoreSettingsUseCaseDep,
    cache: CacheDep,
) -> StoreSettingsResponse:
    use_case = SelectThemeUseCase(
        store_settings_repository, theme_repository, get_store_settings_uc
    )
    settings = await use_case.execute(
        SelectThemeInput(tenant_id=current.tenant_id, theme_id=body.theme_id)
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return StoreSettingsResponse.from_entity(settings)


@router.patch("/store-settings/sections/{section}", response_model=StoreSettingsResponse)
async def toggle_section(
    section: str,
    body: ToggleSectionRequest,
    current: CurrentAdminDep,
    store_settings_repository: StoreSettingsRepositoryDep,
    get_store_settings_uc: GetStoreSettingsUseCaseDep,
    cache: CacheDep,
) -> StoreSettingsResponse:
    use_case = ToggleThemeSectionUseCase(store_settings_repository, get_store_settings_uc)
    settings = await use_case.execute(
        ToggleThemeSectionInput(tenant_id=current.tenant_id, section=section, enabled=body.enabled)
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return StoreSettingsResponse.from_entity(settings)


@router.post("/store-settings/images", response_model=StoreSettingsResponse)
async def upload_store_image(
    current: CurrentAdminDep,
    store_settings_repository: StoreSettingsRepositoryDep,
    get_store_settings_uc: GetStoreSettingsUseCaseDep,
    object_storage: ObjectStorageDep,
    get_effective_plan: GetEffectivePlanUseCaseDep,
    cache: CacheDep,
    kind: ImageKind = Form(...),
    file: UploadFile = File(...),
) -> StoreSettingsResponse:
    use_case = UploadStoreImageUseCase(
        store_settings_repository, get_store_settings_uc, object_storage, get_effective_plan
    )
    content = await file.read()
    settings = await use_case.execute(
        UploadStoreImageInput(
            tenant_id=current.tenant_id,
            kind=kind,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "upload",
        )
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return StoreSettingsResponse.from_entity(settings)
