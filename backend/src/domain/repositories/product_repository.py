from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from src.domain.entities.product import Product, ProductStatus


@dataclass(frozen=True, slots=True)
class ProductFilters:
    category_id: UUID | None = None
    status: ProductStatus | None = None
    min_price: Decimal | None = None
    max_price: Decimal | None = None
    search: str | None = None
    limit: int = 50
    offset: int = 0


class ProductRepository(Protocol):
    async def get_by_id(self, tenant_id: UUID, product_id: UUID) -> Product | None: ...

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Product | None: ...

    async def get_by_sku(self, tenant_id: UUID, sku: str) -> Product | None: ...

    async def count(self, tenant_id: UUID, filters: ProductFilters) -> int: ...

    async def add(self, product: Product) -> Product: ...

    async def update(self, product: Product) -> Product: ...

    async def delete(self, tenant_id: UUID, product_id: UUID) -> None: ...

    async def bulk_update_status(
        self, tenant_id: UUID, product_ids: list[UUID], status: ProductStatus
    ) -> int: ...

    # Defined last: naming this `list` shadows the builtin for any annotation
    # appearing later in this class body (evaluated in the class namespace).
    async def list(self, tenant_id: UUID, filters: ProductFilters) -> list[Product]: ...
