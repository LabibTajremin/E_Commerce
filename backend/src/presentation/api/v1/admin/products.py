from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, File, Query, UploadFile, status

from src.application.use_cases.products.adjust_stock import AdjustStockInput, AdjustStockUseCase
from src.application.use_cases.products.bulk_update_status import (
    BulkUpdateStatusInput,
    BulkUpdateStatusUseCase,
)
from src.application.use_cases.products.create_product import (
    CreateProductInput,
    CreateProductUseCase,
)
from src.application.use_cases.products.list_products import (
    DeleteProductUseCase,
    GetProductUseCase,
    ListProductsUseCase,
)
from src.application.use_cases.products.update_product import (
    UpdateProductInput,
    UpdateProductUseCase,
)
from src.application.use_cases.products.upload_product_image import (
    ReorderProductImagesInput,
    ReorderProductImagesUseCase,
    UploadProductImageInput,
    UploadProductImageUseCase,
)
from src.domain.entities.product import ProductStatus
from src.domain.repositories.product_repository import ProductFilters
from src.presentation.caching import storefront_cache_namespace
from src.presentation.dependencies import (
    CacheDep,
    CategoryRepositoryDep,
    CurrentAdminDep,
    GetEffectivePlanUseCaseDep,
    ObjectStorageDep,
    ProductRepositoryDep,
)
from src.presentation.schemas.product import (
    BulkStatusUpdateRequest,
    ProductCreateRequest,
    ProductPageResponse,
    ProductResponse,
    ProductUpdateRequest,
    ReorderImagesRequest,
    StockAdjustmentRequest,
)

router = APIRouter(prefix="/products", tags=["admin:products"])


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
async def create_product(
    body: ProductCreateRequest,
    current: CurrentAdminDep,
    product_repository: ProductRepositoryDep,
    category_repository: CategoryRepositoryDep,
    get_effective_plan: GetEffectivePlanUseCaseDep,
    cache: CacheDep,
) -> ProductResponse:
    use_case = CreateProductUseCase(product_repository, category_repository, get_effective_plan)
    product = await use_case.execute(
        CreateProductInput(tenant_id=current.tenant_id, **body.model_dump())
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return ProductResponse.from_entity(product)


@router.get("", response_model=ProductPageResponse)
async def list_products(
    current: CurrentAdminDep,
    product_repository: ProductRepositoryDep,
    category_id: UUID | None = Query(default=None),
    status_filter: ProductStatus | None = Query(default=None, alias="status"),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> ProductPageResponse:
    use_case = ListProductsUseCase(product_repository)
    page = await use_case.execute(
        current.tenant_id,
        ProductFilters(
            category_id=category_id,
            status=status_filter,
            min_price=min_price,
            max_price=max_price,
            search=search,
            limit=limit,
            offset=offset,
        ),
    )
    return ProductPageResponse(
        items=[ProductResponse.from_entity(p) for p in page.items], total=page.total
    )


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: UUID, current: CurrentAdminDep, product_repository: ProductRepositoryDep
) -> ProductResponse:
    use_case = GetProductUseCase(product_repository)
    product = await use_case.execute(current.tenant_id, product_id)
    return ProductResponse.from_entity(product)


@router.patch("/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: UUID,
    body: ProductUpdateRequest,
    current: CurrentAdminDep,
    product_repository: ProductRepositoryDep,
    cache: CacheDep,
) -> ProductResponse:
    use_case = UpdateProductUseCase(product_repository)
    product = await use_case.execute(
        UpdateProductInput(
            tenant_id=current.tenant_id, product_id=product_id, **body.model_dump()
        )
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return ProductResponse.from_entity(product)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: UUID,
    current: CurrentAdminDep,
    product_repository: ProductRepositoryDep,
    cache: CacheDep,
) -> None:
    use_case = DeleteProductUseCase(product_repository)
    await use_case.execute(current.tenant_id, product_id)
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))


@router.post("/bulk-status", response_model=dict[str, int])
async def bulk_update_status(
    body: BulkStatusUpdateRequest,
    current: CurrentAdminDep,
    product_repository: ProductRepositoryDep,
    cache: CacheDep,
) -> dict[str, int]:
    use_case = BulkUpdateStatusUseCase(product_repository)
    updated = await use_case.execute(
        BulkUpdateStatusInput(
            tenant_id=current.tenant_id, product_ids=body.product_ids, status=body.status
        )
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return {"updated": updated}


@router.post("/{product_id}/stock", response_model=ProductResponse)
async def adjust_stock(
    product_id: UUID,
    body: StockAdjustmentRequest,
    current: CurrentAdminDep,
    product_repository: ProductRepositoryDep,
    cache: CacheDep,
) -> ProductResponse:
    use_case = AdjustStockUseCase(product_repository)
    product = await use_case.execute(
        AdjustStockInput(tenant_id=current.tenant_id, product_id=product_id, delta=body.delta)
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return ProductResponse.from_entity(product)


@router.post("/{product_id}/images", response_model=ProductResponse)
async def upload_product_image(
    product_id: UUID,
    current: CurrentAdminDep,
    product_repository: ProductRepositoryDep,
    object_storage: ObjectStorageDep,
    cache: CacheDep,
    file: UploadFile = File(...),
) -> ProductResponse:
    use_case = UploadProductImageUseCase(product_repository, object_storage)
    content = await file.read()
    product = await use_case.execute(
        UploadProductImageInput(
            tenant_id=current.tenant_id,
            product_id=product_id,
            content=content,
            content_type=file.content_type or "application/octet-stream",
            filename=file.filename or "upload",
        )
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return ProductResponse.from_entity(product)


@router.put("/{product_id}/images/order", response_model=ProductResponse)
async def reorder_product_images(
    product_id: UUID,
    body: ReorderImagesRequest,
    current: CurrentAdminDep,
    product_repository: ProductRepositoryDep,
    cache: CacheDep,
) -> ProductResponse:
    use_case = ReorderProductImagesUseCase(product_repository)
    product = await use_case.execute(
        ReorderProductImagesInput(
            tenant_id=current.tenant_id, product_id=product_id, ordered_urls=body.ordered_urls
        )
    )
    await cache.bump_version(storefront_cache_namespace(current.tenant_id))
    return ProductResponse.from_entity(product)
