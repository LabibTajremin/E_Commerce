from typing import Protocol
from uuid import UUID

from src.domain.entities.cart import Cart


class CartRepository(Protocol):
    async def get_by_customer(self, tenant_id: UUID, customer_id: UUID) -> Cart | None: ...

    async def get_by_session(self, tenant_id: UUID, session_id: str) -> Cart | None: ...

    async def upsert(self, cart: Cart) -> Cart: ...

    async def delete(self, tenant_id: UUID, cart_id: UUID) -> None: ...
