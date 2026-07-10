from uuid import UUID

from fastapi import APIRouter, status

from src.application.use_cases.categories.create_category import (
    CreateCategoryInput,
    CreateCategoryUseCase,
)
from src.application.use_cases.categories.update_category import (
    DeleteCategoryUseCase,
    ListCategoriesUseCase,
    UpdateCategoryInput,
    UpdateCategoryUseCase,
)
from src.presentation.caching import storefront_cache_namespace
from src.presentation.dependencies import CacheDep, CategoryRepositoryDep, CurrentAdminDep
from src.presentation.schemas.category import (
    CategoryCreateRequest,
    CategoryResponse,
    CategoryUpdateRequest,
)

router = APIRouter(prefix="/categories", tags=["admin:categories"])


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    body: CategoryCreateRequest,
    current: CurrentAdminDep,
    category_repository: CategoryRepositoryDep,
    cache: CacheDep,
) -> CategoryResponse:
    use_case = CreateCategoryUseCase(category_repository)
    category = await use_case.execute(
        CreateCategoryInput(
            tenant_id=current.tenant_id, name=body.name, slug=body.slug, parent_id=body.parent_id
        )
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return CategoryResponse.from_entity(category)


@router.get("", response_model=list[CategoryResponse])
async def list_categories(
    current: CurrentAdminDep, category_repository: CategoryRepositoryDep
) -> list[CategoryResponse]:
    use_case = ListCategoriesUseCase(category_repository)
    categories = await use_case.execute(current.tenant_id)
    return [CategoryResponse.from_entity(c) for c in categories]


@router.patch("/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: UUID,
    body: CategoryUpdateRequest,
    current: CurrentAdminDep,
    category_repository: CategoryRepositoryDep,
    cache: CacheDep,
) -> CategoryResponse:
    use_case = UpdateCategoryUseCase(category_repository)
    category = await use_case.execute(
        UpdateCategoryInput(
            tenant_id=current.tenant_id,
            category_id=category_id,
            name=body.name,
            parent_id=body.parent_id,
        )
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return CategoryResponse.from_entity(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: UUID,
    current: CurrentAdminDep,
    category_repository: CategoryRepositoryDep,
    cache: CacheDep,
) -> None:
    use_case = DeleteCategoryUseCase(category_repository)
    await use_case.execute(current.tenant_id, category_id)
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
