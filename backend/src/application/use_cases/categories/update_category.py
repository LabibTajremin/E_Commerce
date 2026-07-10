from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.category import Category
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.repositories.category_repository import CategoryRepository


@dataclass(frozen=True, slots=True)
class UpdateCategoryInput:
    tenant_id: UUID
    category_id: UUID
    name: str | None = None
    parent_id: UUID | None = None


class UpdateCategoryUseCase:
    def __init__(self, category_repository: CategoryRepository) -> None:
        self._categories = category_repository

    async def execute(self, data: UpdateCategoryInput) -> Category:
        category = await self._categories.get_by_id(data.tenant_id, data.category_id)
        if category is None:
            raise EntityNotFoundError("Category", data.category_id)

        if data.name is not None:
            category.name = data.name
        if data.parent_id is not None:
            if data.parent_id == category.id:
                raise ValidationError("A category cannot be its own parent")
            category.parent_id = data.parent_id

        return await self._categories.update(category)


class DeleteCategoryUseCase:
    def __init__(self, category_repository: CategoryRepository) -> None:
        self._categories = category_repository

    async def execute(self, tenant_id: UUID, category_id: UUID) -> None:
        await self._categories.delete(tenant_id, category_id)


class ListCategoriesUseCase:
    def __init__(self, category_repository: CategoryRepository) -> None:
        self._categories = category_repository

    async def execute(self, tenant_id: UUID) -> list[Category]:
        return await self._categories.list(tenant_id)
