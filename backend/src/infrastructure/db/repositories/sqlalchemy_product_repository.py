from typing import Any
from uuid import UUID

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.product import Product, ProductStatus
from src.domain.repositories.product_repository import ProductFilters
from src.domain.value_objects.money import Money
from src.domain.value_objects.sku import SKU
from src.domain.value_objects.slug import Slug
from src.infrastructure.db.models.product import ProductModel


class SqlAlchemyProductRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: ProductModel) -> Product:
        return Product(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            slug=Slug(model.slug),
            description=model.description,
            price=Money(model.price),
            compare_at_price=Money(model.compare_at_price) if model.compare_at_price else None,
            sku=SKU(model.sku) if model.sku else None,
            images=list(model.images),
            stock_qty=model.stock_qty,
            status=ProductStatus(model.status),
            category_id=model.category_id,
            created_at=model.created_at,
        )

    def _apply_filters(
        self, query: Select[Any], tenant_id: UUID, filters: ProductFilters
    ) -> Select[Any]:
        query = query.where(ProductModel.tenant_id == tenant_id)
        if filters.category_id is not None:
            query = query.where(ProductModel.category_id == filters.category_id)
        if filters.status is not None:
            query = query.where(ProductModel.status == filters.status.value)
        if filters.min_price is not None:
            query = query.where(ProductModel.price >= filters.min_price)
        if filters.max_price is not None:
            query = query.where(ProductModel.price <= filters.max_price)
        if filters.search:
            query = query.where(
                ProductModel.search_vector.op("@@")(func.plainto_tsquery("english", filters.search))
            )
        return query

    async def get_by_id(self, tenant_id: UUID, product_id: UUID) -> Product | None:
        result = await self._session.execute(
            select(ProductModel).where(
                ProductModel.id == product_id, ProductModel.tenant_id == tenant_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_id_for_update(self, tenant_id: UUID, product_id: UUID) -> Product | None:
        result = await self._session.execute(
            select(ProductModel)
            .where(ProductModel.id == product_id, ProductModel.tenant_id == tenant_id)
            .with_for_update()
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Product | None:
        result = await self._session.execute(
            select(ProductModel).where(
                ProductModel.tenant_id == tenant_id, ProductModel.slug == slug
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_sku(self, tenant_id: UUID, sku: str) -> Product | None:
        result = await self._session.execute(
            select(ProductModel).where(
                ProductModel.tenant_id == tenant_id, ProductModel.sku == sku
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def count(self, tenant_id: UUID, filters: ProductFilters) -> int:
        query = self._apply_filters(select(func.count(ProductModel.id)), tenant_id, filters)
        result = await self._session.execute(query)
        return int(result.scalar_one())

    async def add(self, product: Product) -> Product:
        model = ProductModel(
            id=product.id,
            tenant_id=product.tenant_id,
            name=product.name,
            slug=str(product.slug),
            description=product.description,
            price=product.price.amount,
            compare_at_price=product.compare_at_price.amount if product.compare_at_price else None,
            sku=str(product.sku) if product.sku else None,
            images=list(product.images),
            stock_qty=product.stock_qty,
            status=product.status.value,
            category_id=product.category_id,
            created_at=product.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, product: Product) -> Product:
        result = await self._session.execute(
            select(ProductModel).where(
                ProductModel.id == product.id, ProductModel.tenant_id == product.tenant_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Product not found: {product.id}")
        model.name = product.name
        model.slug = str(product.slug)
        model.description = product.description
        model.price = product.price.amount
        model.compare_at_price = (
            product.compare_at_price.amount if product.compare_at_price else None
        )
        model.sku = str(product.sku) if product.sku else None
        model.images = list(product.images)
        model.stock_qty = product.stock_qty
        model.status = product.status.value
        model.category_id = product.category_id
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, tenant_id: UUID, product_id: UUID) -> None:
        result = await self._session.execute(
            select(ProductModel).where(
                ProductModel.id == product_id, ProductModel.tenant_id == tenant_id
            )
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()

    async def bulk_update_status(
        self, tenant_id: UUID, product_ids: list[UUID], status: ProductStatus
    ) -> int:
        result = await self._session.execute(
            select(ProductModel).where(
                ProductModel.tenant_id == tenant_id, ProductModel.id.in_(product_ids)
            )
        )
        models = list(result.scalars().all())
        for model in models:
            model.status = status.value
        await self._session.flush()
        return len(models)

    # Defined last: naming this `list` shadows the builtin for any annotation
    # appearing later in this class body (evaluated in the class namespace).
    async def list(self, tenant_id: UUID, filters: ProductFilters) -> list[Product]:
        query = self._apply_filters(select(ProductModel), tenant_id, filters)
        query = query.order_by(ProductModel.created_at.desc()).limit(filters.limit).offset(
            filters.offset
        )
        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]
