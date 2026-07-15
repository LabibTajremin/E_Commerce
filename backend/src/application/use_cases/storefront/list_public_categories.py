from uuid import UUID

from src.domain.entities.category import Category
from src.domain.repositories.category_repository import CategoryRepository


class ListPublicCategoriesUseCase:
    def __init__(self, category_repository: CategoryRepository) -> None:
        self._categories = category_repository

    async def execute(self, tenant_id: UUID) -> list[Category]:
        return await self._categories.list(tenant_id)
