from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.domain.entities.product import Product
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.repositories.product_repository import ProductRepository
from src.domain.value_objects.money import Money
from src.domain.value_objects.sku import SKU


@dataclass(frozen=True, slots=True)
class UpdateProductInput:
    tenant_id: UUID
    product_id: UUID
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    compare_at_price: Decimal | None = None
    sku: str | None = None
    category_id: UUID | None = None


class UpdateProductUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, data: UpdateProductInput) -> Product:
        product = await self._products.get_by_id(data.tenant_id, data.product_id)
        if product is None:
            raise EntityNotFoundError("Product", data.product_id)

        if data.name is not None:
            product.name = data.name
        if data.description is not None:
            product.description = data.description
        if data.price is not None:
            product.price = Money(data.price)
        if data.compare_at_price is not None:
            product.compare_at_price = Money(data.compare_at_price)
        if data.sku is not None:
            product.sku = SKU(data.sku)
        if data.category_id is not None:
            product.category_id = data.category_id

        if (
            product.compare_at_price is not None
            and product.compare_at_price.amount < product.price.amount
        ):
            raise ValidationError("compare_at_price cannot be less than price")

        return await self._products.update(product)
