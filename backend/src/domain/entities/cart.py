from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4

from src.domain.exceptions import ValidationError


@dataclass(slots=True)
class CartLineItem:
    product_id: UUID
    quantity: int

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValidationError("Cart line item quantity must be positive")


@dataclass(slots=True)
class Cart:
    tenant_id: UUID
    id: UUID = field(default_factory=uuid4)
    customer_id: UUID | None = None
    session_id: str | None = None
    line_items: list[CartLineItem] = field(default_factory=list)
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.customer_id is None and self.session_id is None:
            raise ValidationError("Cart must belong to either a customer or a session")

    def add_item(self, product_id: UUID, quantity: int) -> None:
        if quantity <= 0:
            raise ValidationError("Quantity must be positive")
        for item in self.line_items:
            if item.product_id == product_id:
                item.quantity += quantity
                return
        self.line_items.append(CartLineItem(product_id=product_id, quantity=quantity))

    def set_item_quantity(self, product_id: UUID, quantity: int) -> None:
        if quantity <= 0:
            self.remove_item(product_id)
            return
        for item in self.line_items:
            if item.product_id == product_id:
                item.quantity = quantity
                return
        self.line_items.append(CartLineItem(product_id=product_id, quantity=quantity))

    def remove_item(self, product_id: UUID) -> None:
        self.line_items = [i for i in self.line_items if i.product_id != product_id]

    def clear(self) -> None:
        self.line_items = []
