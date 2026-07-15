from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.order import Order, OrderStatus
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.order_repository import OrderFilters, OrderRepository


@dataclass(frozen=True, slots=True)
class OrderPage:
    items: list[Order]
    total: int


class ListOrdersUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._orders = order_repository

    async def execute(self, tenant_id: UUID, filters: OrderFilters) -> OrderPage:
        items = await self._orders.list(tenant_id, filters)
        total = await self._orders.count(tenant_id, filters)
        return OrderPage(items=items, total=total)


class GetOrderUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._orders = order_repository

    async def execute(self, tenant_id: UUID, order_id: UUID) -> Order:
        order = await self._orders.get_by_id(tenant_id, order_id)
        if order is None:
            raise EntityNotFoundError("Order", order_id)
        return order


@dataclass(frozen=True, slots=True)
class UpdateOrderStatusInput:
    tenant_id: UUID
    order_id: UUID
    new_status: OrderStatus


class UpdateOrderStatusUseCase:
    def __init__(self, order_repository: OrderRepository) -> None:
        self._orders = order_repository

    async def execute(self, data: UpdateOrderStatusInput) -> Order:
        order = await self._orders.get_by_id(data.tenant_id, data.order_id)
        if order is None:
            raise EntityNotFoundError("Order", data.order_id)
        order.transition_to(data.new_status)
        return await self._orders.update(order)
