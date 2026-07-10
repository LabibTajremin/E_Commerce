from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.category import Category
from src.domain.value_objects.slug import Slug
from src.infrastructure.db.models.category import CategoryModel


class SqlAlchemyCategoryRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: CategoryModel) -> Category:
        return Category(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            slug=Slug(model.slug),
            parent_id=model.parent_id,
        )

    async def get_by_id(self, tenant_id: UUID, category_id: UUID) -> Category | None:
        result = await self._session.execute(
            select(CategoryModel).where(
                CategoryModel.id == category_id, CategoryModel.tenant_id == tenant_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Category | None:
        result = await self._session.execute(
            select(CategoryModel).where(
                CategoryModel.tenant_id == tenant_id, CategoryModel.slug == slug
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(self, tenant_id: UUID) -> list[Category]:
        result = await self._session.execute(
            select(CategoryModel)
            .where(CategoryModel.tenant_id == tenant_id)
            .order_by(CategoryModel.name)
        )
        return [self._to_entity(m) for m in result.scalars().all()]

    async def add(self, category: Category) -> Category:
        model = CategoryModel(
            id=category.id,
            tenant_id=category.tenant_id,
            name=category.name,
            slug=str(category.slug),
            parent_id=category.parent_id,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, category: Category) -> Category:
        result = await self._session.execute(
            select(CategoryModel).where(
                CategoryModel.id == category.id, CategoryModel.tenant_id == category.tenant_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Category not found: {category.id}")
        model.name = category.name
        model.slug = str(category.slug)
        model.parent_id = category.parent_id
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, tenant_id: UUID, category_id: UUID) -> None:
        result = await self._session.execute(
            select(CategoryModel).where(
                CategoryModel.id == category_id, CategoryModel.tenant_id == tenant_id
            )
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
