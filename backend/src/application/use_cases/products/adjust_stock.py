from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.product import Product
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.product_repository import ProductRepository


@dataclass(frozen=True, slots=True)
class AdjustStockInput:
    tenant_id: UUID
    product_id: UUID
    delta: int


class AdjustStockUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, data: AdjustStockInput) -> Product:
        product = await self._products.get_by_id(data.tenant_id, data.product_id)
        if product is None:
            raise EntityNotFoundError("Product", data.product_id)
        product.adjust_stock(data.delta)
        return await self._products.update(product)
