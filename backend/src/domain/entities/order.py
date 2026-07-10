from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from src.domain.exceptions import ValidationError
from src.domain.value_objects.address import Address
from src.domain.value_objects.money import Money


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class PaymentStatus(StrEnum):
    UNPAID = "unpaid"
    PAID = "paid"
    REFUNDED = "refunded"


_ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.PENDING: {OrderStatus.PAID, OrderStatus.CANCELLED},
    OrderStatus.PAID: {OrderStatus.FULFILLED, OrderStatus.REFUNDED, OrderStatus.CANCELLED},
    OrderStatus.FULFILLED: {OrderStatus.REFUNDED},
    OrderStatus.CANCELLED: set(),
    OrderStatus.REFUNDED: set(),
}


@dataclass(slots=True)
class OrderLineItem:
    product_id: UUID
    product_name: str
    unit_price: Money
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValidationError("Order line item quantity must be positive")

    @property
    def line_total(self) -> Decimal:
        return (self.unit_price.amount * self.quantity).quantize(Decimal("0.01"))


@dataclass(slots=True)
class Order:
    tenant_id: UUID
    customer_id: UUID
    line_items: list[OrderLineItem]
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total: Decimal
    shipping_address: Address
    id: UUID = field(default_factory=uuid4)
    status: OrderStatus = OrderStatus.PENDING
    payment_status: PaymentStatus = PaymentStatus.UNPAID
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if not self.line_items:
            raise ValidationError("Order must have at least one line item")

    def transition_to(self, new_status: OrderStatus) -> None:
        allowed = _ALLOWED_TRANSITIONS[self.status]
        if new_status not in allowed:
            raise ValidationError(f"Cannot transition order from {self.status} to {new_status}")
        self.status = new_status
        if new_status == OrderStatus.PAID:
            self.payment_status = PaymentStatus.PAID
        elif new_status == OrderStatus.REFUNDED:
            self.payment_status = PaymentStatus.REFUNDED
