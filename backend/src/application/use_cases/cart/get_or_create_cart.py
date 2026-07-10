from dataclasses import dataclass
from uuid import UUID

from src.domain.entities.cart import Cart
from src.domain.repositories.cart_repository import CartRepository


@dataclass(frozen=True, slots=True)
class CartIdentity:
    tenant_id: UUID
    customer_id: UUID | None = None
    session_id: str | None = None


class GetOrCreateCartUseCase:
    def __init__(self, cart_repository: CartRepository) -> None:
        self._carts = cart_repository

    async def execute(self, identity: CartIdentity) -> Cart:
        if identity.customer_id is not None:
            existing = await self._carts.get_by_customer(identity.tenant_id, identity.customer_id)
        else:
            assert identity.session_id is not None
            existing = await self._carts.get_by_session(identity.tenant_id, identity.session_id)

        if existing is not None:
            return existing

        cart = Cart(
            tenant_id=identity.tenant_id,
            customer_id=identity.customer_id,
            session_id=identity.session_id,
        )
        return await self._carts.upsert(cart)
