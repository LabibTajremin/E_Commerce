from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities.cart import Cart


class AddCartItemRequest(BaseModel):
    product_id: UUID
    quantity: int = Field(gt=0)


class UpdateCartItemRequest(BaseModel):
    quantity: int = Field(ge=0)


class CartLineItemResponse(BaseModel):
    product_id: UUID
    quantity: int


class CartResponse(BaseModel):
    id: UUID
    line_items: list[CartLineItemResponse]

    @classmethod
    def from_entity(cls, cart: Cart) -> "CartResponse":
        return cls(
            id=cart.id,
            line_items=[
                CartLineItemResponse(product_id=i.product_id, quantity=i.quantity)
                for i in cart.line_items
            ],
        )
