from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.product import Product
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.product_repository import ProductFilters, ProductRepository


@dataclass(frozen=True, slots=True)
class ProductPage:
    items: list[Product]
    total: int


class ListProductsUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, tenant_id: UUID, filters: ProductFilters) -> ProductPage:
        items = await self._products.list(tenant_id, filters)
        total = await self._products.count(tenant_id, filters)
        return ProductPage(items=items, total=total)


class GetProductUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, tenant_id: UUID, product_id: UUID) -> Product:
        product = await self._products.get_by_id(tenant_id, product_id)
        if product is None:
            raise EntityNotFoundError("Product", product_id)
        return product


class DeleteProductUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, tenant_id: UUID, product_id: UUID) -> None:
        await self._products.delete(tenant_id, product_id)
