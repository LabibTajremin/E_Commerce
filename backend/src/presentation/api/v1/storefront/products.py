from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Query

from src.application.use_cases.storefront.get_public_product import (
    GetPublicProductBySlugUseCase,
)
from src.application.use_cases.storefront.list_public_products import (
    ListPublicProductsUseCase,
    PublicProductFilters,
)
from src.presentation.caching import cached_get_or_compute
from src.presentation.dependencies import CacheDep, ProductRepositoryDep, ResolvedTenantIdDep
from src.presentation.schemas.storefront import PublicProductPageResponse, PublicProductResponse

router = APIRouter(tags=["storefront:products"])


@router.get("/products", response_model=PublicProductPageResponse)
async def list_public_products(
    tenant_id: ResolvedTenantIdDep,
    product_repository: ProductRepositoryDep,
    cache: CacheDep,
    category_id: UUID | None = Query(default=None),
    min_price: Decimal | None = Query(default=None, ge=0),
    max_price: Decimal | None = Query(default=None, ge=0),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> PublicProductPageResponse:
    assert tenant_id is not None  # tenant resolution middleware guarantees this

    async def compute() -> PublicProductPageResponse:
        use_case = ListPublicProductsUseCase(product_repository)
        page = await use_case.execute(
            tenant_id,
            PublicProductFilters(
                category_id=category_id,
                min_price=min_price,
                max_price=max_price,
                search=search,
                limit=limit,
                offset=offset,
            ),
        )
        return PublicProductPageResponse(
            items=[PublicProductResponse.from_entity(p) for p in page.items], total=page.total
        )

    key_parts = f"{category_id}:{min_price}:{max_price}:{search}:{limit}:{offset}"
    return await cached_get_or_compute(
        cache=cache,
        tenant_id=tenant_id,
        resource="products",
        key_parts=key_parts,
        compute=compute,
        model=PublicProductPageResponse,
    )


@router.get("/products/{slug}", response_model=PublicProductResponse)
async def get_public_product(
    slug: str,
    tenant_id: ResolvedTenantIdDep,
    product_repository: ProductRepositoryDep,
    cache: CacheDep,
) -> PublicProductResponse:
    assert tenant_id is not None

    async def compute() -> PublicProductResponse:
        use_case = GetPublicProductBySlugUseCase(product_repository)
        product = await use_case.execute(tenant_id, slug)
        return PublicProductResponse.from_entity(product)

    return await cached_get_or_compute(
        cache=cache,
        tenant_id=tenant_id,
        resource="product",
        key_parts=slug,
        compute=compute,
        model=PublicProductResponse,
    )
