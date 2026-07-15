from uuid import UUID

from src.domain.entities.product import Product, ProductStatus
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.product_repository import ProductRepository


class GetPublicProductBySlugUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, tenant_id: UUID, slug: str) -> Product:
        product = await self._products.get_by_slug(tenant_id, slug)
        # A draft product 404s exactly like a nonexistent one — the slug's
        # existence must not be inferable from the response.
        if product is None or product.status != ProductStatus.PUBLISHED:
            raise EntityNotFoundError("Product", slug)
        return product
