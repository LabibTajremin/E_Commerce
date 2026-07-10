from dataclasses import dataclass
from uuid import UUID

from src.application.use_cases._slug import generate_unique_slug
from src.domain.entities.category import Category
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.category_repository import CategoryRepository


@dataclass(frozen=True, slots=True)
class CreateCategoryInput:
    tenant_id: UUID
    name: str
    slug: str | None = None
    parent_id: UUID | None = None


class CreateCategoryUseCase:
    def __init__(self, category_repository: CategoryRepository) -> None:
        self._categories = category_repository

    async def execute(self, data: CreateCategoryInput) -> Category:
        if data.parent_id is not None:
            parent = await self._categories.get_by_id(data.tenant_id, data.parent_id)
            if parent is None:
                raise EntityNotFoundError("Category", data.parent_id)

        async def slug_exists(slug: str) -> bool:
            return await self._categories.get_by_slug(data.tenant_id, slug) is not None

        slug = await generate_unique_slug(data.slug or data.name, slug_exists)

        category = Category(
            tenant_id=data.tenant_id, name=data.name, slug=slug, parent_id=data.parent_id
        )
        return await self._categories.add(category)
