from fastapi import APIRouter

from src.application.use_cases.storefront.list_public_categories import (
    ListPublicCategoriesUseCase,
)
from src.presentation.caching import cached_get_or_compute
from src.presentation.dependencies import CacheDep, CategoryRepositoryDep, ResolvedTenantIdDep
from src.presentation.schemas.storefront import PublicCategoryListResponse, PublicCategoryResponse

router = APIRouter(tags=["storefront:categories"])


@router.get("/categories", response_model=PublicCategoryListResponse)
async def list_public_categories(
    tenant_id: ResolvedTenantIdDep,
    category_repository: CategoryRepositoryDep,
    cache: CacheDep,
) -> PublicCategoryListResponse:
    assert tenant_id is not None

    async def compute() -> PublicCategoryListResponse:
        use_case = ListPublicCategoriesUseCase(category_repository)
        categories = await use_case.execute(tenant_id)
        return PublicCategoryListResponse(
            items=[PublicCategoryResponse.from_entity(c) for c in categories]
        )

    return await cached_get_or_compute(
        cache=cache,
        tenant_id=tenant_id,
        resource="categories",
        key_parts="all",
        compute=compute,
        model=PublicCategoryListResponse,
    )
