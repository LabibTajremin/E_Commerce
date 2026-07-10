from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.domain.entities.product import Product, ProductStatus
from src.domain.repositories.product_repository import ProductFilters, ProductRepository


@dataclass(frozen=True, slots=True)
class PublicProductFilters:
    category_id: UUID | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    search: str | None = None
    limit: int = 50
    offset: int = 0


@dataclass(frozen=True, slots=True)
class PublicProductPage:
    items: list[Product]
    total: int


class ListPublicProductsUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, tenant_id: UUID, filters: PublicProductFilters) -> PublicProductPage:
        # Storefront reads are always forced to published-only regardless of
        # client input — there is no way to request draft products publicly.
        product_filters = ProductFilters(
            category_id=filters.category_id,
            status=ProductStatus.PUBLISHED,
            min_price=filters.min_price,
            max_price=filters.max_price,
            search=filters.search,
            limit=filters.limit,
            offset=filters.offset,
        )
        items = await self._products.list(tenant_id, product_filters)
        total = await self._products.count(tenant_id, product_filters)
        return PublicProductPage(items=items, total=total)
