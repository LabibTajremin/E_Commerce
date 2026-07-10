from dataclasses import asdict
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.domain.entities.order import Order, OrderLineItem, OrderStatus, PaymentStatus
from src.domain.repositories.order_repository import OrderFilters
from src.domain.value_objects.address import Address
from src.domain.value_objects.money import Money
from src.infrastructure.db.models.order import OrderLineItemModel, OrderModel


class SqlAlchemyOrderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: OrderModel) -> Order:
        return Order(
            id=model.id,
            tenant_id=model.tenant_id,
            customer_id=model.customer_id,
            line_items=[
                OrderLineItem(
                    product_id=li.product_id,
                    product_name=li.product_name,
                    unit_price=Money(li.unit_price),
                    quantity=li.quantity,
                )
                for li in model.line_items
            ],
            subtotal=model.subtotal,
            tax=model.tax,
            shipping=model.shipping,
            total=model.total,
            shipping_address=Address(**model.shipping_address),
            status=OrderStatus(model.status),
            payment_status=PaymentStatus(model.payment_status),
            created_at=model.created_at,
        )

    async def get_by_id(self, tenant_id: UUID, order_id: UUID) -> Order | None:
        result = await self._session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.line_items))
            .where(OrderModel.id == order_id, OrderModel.tenant_id == tenant_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def add(self, order: Order) -> Order:
        model = OrderModel(
            id=order.id,
            tenant_id=order.tenant_id,
            customer_id=order.customer_id,
            status=order.status.value,
            payment_status=order.payment_status.value,
            subtotal=order.subtotal,
            tax=order.tax,
            shipping=order.shipping,
            total=order.total,
            shipping_address=asdict(order.shipping_address),
            created_at=order.created_at,
        )
        model.line_items = [
            OrderLineItemModel(
                product_id=li.product_id,
                product_name=li.product_name,
                unit_price=li.unit_price.amount,
                quantity=li.quantity,
            )
            for li in order.line_items
        ]
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, order: Order) -> Order:
        result = await self._session.execute(
            select(OrderModel)
            .options(selectinload(OrderModel.line_items))
            .where(OrderModel.id == order.id, OrderModel.tenant_id == order.tenant_id)
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"Order not found: {order.id}")
        model.status = order.status.value
        model.payment_status = order.payment_status.value
        await self._session.flush()
        return self._to_entity(model)

    def _apply_filters(self, tenant_id: UUID, filters: OrderFilters) -> list[Any]:
        conditions: list[Any] = [OrderModel.tenant_id == tenant_id]
        if filters.customer_id is not None:
            conditions.append(OrderModel.customer_id == filters.customer_id)
        if filters.status is not None:
            conditions.append(OrderModel.status == filters.status.value)
        return conditions

    async def count(self, tenant_id: UUID, filters: OrderFilters) -> int:
        query = select(func.count(OrderModel.id)).where(*self._apply_filters(tenant_id, filters))
        result = await self._session.execute(query)
        return int(result.scalar_one())

    async def list(self, tenant_id: UUID, filters: OrderFilters) -> list[Order]:
        query = (
            select(OrderModel)
            .options(selectinload(OrderModel.line_items))
            .where(*self._apply_filters(tenant_id, filters))
            .order_by(OrderModel.created_at.desc())
            .limit(filters.limit)
            .offset(filters.offset)
        )
        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]
