from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from src.domain.entities.order import Order, OrderStatus


@dataclass(frozen=True, slots=True)
class OrderFilters:
    customer_id: UUID | None = None
    status: OrderStatus | None = None
    limit: int = 50
    offset: int = 0


class OrderRepository(Protocol):
    async def get_by_id(self, tenant_id: UUID, order_id: UUID) -> Order | None: ...

    async def add(self, order: Order) -> Order: ...

    async def update(self, order: Order) -> Order: ...

    async def count(self, tenant_id: UUID, filters: OrderFilters) -> int: ...

    # Defined last: naming this `list` shadows the builtin for any annotation
    # appearing later in this class body (evaluated in the class namespace).
    async def list(self, tenant_id: UUID, filters: OrderFilters) -> list[Order]: ...
