from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.product import ProductStatus
from src.domain.repositories.product_repository import ProductRepository


@dataclass(frozen=True, slots=True)
class BulkUpdateStatusInput:
    tenant_id: UUID
    product_ids: list[UUID]
    status: ProductStatus


class BulkUpdateStatusUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, data: BulkUpdateStatusInput) -> int:
        return await self._products.bulk_update_status(
            data.tenant_id, data.product_ids, data.status
        )
