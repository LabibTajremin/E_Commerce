from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities.order import Order, OrderStatus


class ShippingAddressRequest(BaseModel):
    line1: str = Field(min_length=1)
    line2: str | None = None
    city: str = Field(min_length=1)
    state: str = Field(min_length=1)
    postal_code: str = Field(min_length=1)
    country: str = Field(min_length=1)


class CheckoutRequest(BaseModel):
    shipping_address: ShippingAddressRequest


class OrderLineItemResponse(BaseModel):
    product_id: UUID
    product_name: str
    unit_price: Decimal
    quantity: int
    line_total: Decimal


class OrderResponse(BaseModel):
    id: UUID
    customer_id: UUID
    status: OrderStatus
    payment_status: str
    line_items: list[OrderLineItemResponse]
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total: Decimal

    @classmethod
    def from_entity(cls, order: Order) -> "OrderResponse":
        return cls(
            id=order.id,
            customer_id=order.customer_id,
            status=order.status,
            payment_status=order.payment_status.value,
            line_items=[
                OrderLineItemResponse(
                    product_id=li.product_id,
                    product_name=li.product_name,
                    unit_price=li.unit_price.amount,
                    quantity=li.quantity,
                    line_total=li.line_total,
                )
                for li in order.line_items
            ],
            subtotal=order.subtotal,
            tax=order.tax,
            shipping=order.shipping,
            total=order.total,
        )


class OrderPageResponse(BaseModel):
    items: list[OrderResponse]
    total: int


class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus
