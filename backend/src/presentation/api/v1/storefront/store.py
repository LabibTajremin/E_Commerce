from fastapi import APIRouter

from src.presentation.caching import cached_get_or_compute
from src.presentation.dependencies import CacheDep, GetStoreSettingsUseCaseDep, ResolvedTenantIdDep
from src.presentation.schemas.storefront import PublicStoreSettingsResponse

router = APIRouter(tags=["storefront:store"])


@router.get("/store", response_model=PublicStoreSettingsResponse)
async def get_public_store_settings(
    tenant_id: ResolvedTenantIdDep,
    get_store_settings_uc: GetStoreSettingsUseCaseDep,
    cache: CacheDep,
) -> PublicStoreSettingsResponse:
    assert tenant_id is not None

    async def compute() -> PublicStoreSettingsResponse:
        settings = await get_store_settings_uc.execute(tenant_id)
        return PublicStoreSettingsResponse.from_entity(settings)

    return await cached_get_or_compute(
        cache=cache,
        tenant_id=tenant_id,
        resource="store-settings",
        key_parts="all",
        compute=compute,
        model=PublicStoreSettingsResponse,
    )
