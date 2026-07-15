from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.cart import Cart, CartLineItem
from src.infrastructure.db.models.cart import CartModel


class SqlAlchemyCartRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: CartModel) -> Cart:
        line_items = []
        for raw in model.line_items:
            product_id = str(raw["product_id"])
            quantity = raw["quantity"]
            line_items.append(
                CartLineItem(product_id=UUID(product_id), quantity=int(str(quantity)))
            )
        return Cart(
            id=model.id,
            tenant_id=model.tenant_id,
            customer_id=model.customer_id,
            session_id=model.session_id,
            line_items=line_items,
            updated_at=model.updated_at,
        )

    async def get_by_customer(self, tenant_id: UUID, customer_id: UUID) -> Cart | None:
        result = await self._session.execute(
            select(CartModel).where(
                CartModel.tenant_id == tenant_id, CartModel.customer_id == customer_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_session(self, tenant_id: UUID, session_id: str) -> Cart | None:
        result = await self._session.execute(
            select(CartModel).where(
                CartModel.tenant_id == tenant_id, CartModel.session_id == session_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def upsert(self, cart: Cart) -> Cart:
        result = await self._session.execute(select(CartModel).where(CartModel.id == cart.id))
        model = result.scalar_one_or_none()
        line_items_json = [
            {"product_id": str(li.product_id), "quantity": li.quantity} for li in cart.line_items
        ]
        if model is None:
            model = CartModel(
                id=cart.id,
                tenant_id=cart.tenant_id,
                customer_id=cart.customer_id,
                session_id=cart.session_id,
                line_items=line_items_json,
            )
            self._session.add(model)
        else:
            model.line_items = line_items_json
        await self._session.flush()
        return self._to_entity(model)

    async def delete(self, tenant_id: UUID, cart_id: UUID) -> None:
        result = await self._session.execute(
            select(CartModel).where(CartModel.id == cart_id, CartModel.tenant_id == tenant_id)
        )
        model = result.scalar_one_or_none()
        if model is not None:
            await self._session.delete(model)
            await self._session.flush()
