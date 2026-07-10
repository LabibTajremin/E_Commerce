from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.entities.cart import Cart, CartLineItem
from src.domain.entities.order import Order, OrderLineItem, OrderStatus
from src.domain.exceptions import ValidationError
from src.domain.services.pricing import (
    FLAT_SHIPPING_FEE,
    FREE_SHIPPING_THRESHOLD,
    TAX_RATE,
    calculate_totals,
)
from src.domain.value_objects.address import Address
from src.domain.value_objects.money import Money


def _line_item(price: str, qty: int) -> OrderLineItem:
    return OrderLineItem(
        product_id=uuid4(), product_name="Widget", unit_price=Money(Decimal(price)), quantity=qty
    )


def _address() -> Address:
    return Address(
        line1="1 Main St", city="Metropolis", state="CA", postal_code="90210", country="US"
    )


def test_order_line_item_line_total() -> None:
    item = _line_item("9.99", 3)
    assert item.line_total == Decimal("29.97")


def test_calculate_totals_applies_flat_shipping_below_threshold() -> None:
    items = [_line_item("10.00", 1)]

    totals = calculate_totals(items)

    assert totals.subtotal == Decimal("10.00")
    assert totals.tax == (Decimal("10.00") * TAX_RATE).quantize(Decimal("0.01"))
    assert totals.shipping == FLAT_SHIPPING_FEE
    assert totals.total == totals.subtotal + totals.tax + totals.shipping


def test_calculate_totals_free_shipping_at_threshold() -> None:
    items = [_line_item(str(FREE_SHIPPING_THRESHOLD), 1)]

    totals = calculate_totals(items)

    assert totals.shipping == Decimal("0.00")


def test_calculate_totals_matches_line_items_exactly() -> None:
    items = [_line_item("12.50", 2), _line_item("3.33", 3)]

    totals = calculate_totals(items)

    expected_subtotal = Decimal("12.50") * 2 + Decimal("3.33") * 3
    assert totals.subtotal == expected_subtotal.quantize(Decimal("0.01"))


def test_order_requires_at_least_one_line_item() -> None:
    with pytest.raises(ValidationError):
        Order(
            tenant_id=uuid4(),
            customer_id=uuid4(),
            line_items=[],
            subtotal=Decimal("0"),
            tax=Decimal("0"),
            shipping=Decimal("0"),
            total=Decimal("0"),
            shipping_address=_address(),
        )


def _order(status: OrderStatus = OrderStatus.PENDING) -> Order:
    return Order(
        tenant_id=uuid4(),
        customer_id=uuid4(),
        line_items=[_line_item("10.00", 1)],
        subtotal=Decimal("10.00"),
        tax=Decimal("0.80"),
        shipping=Decimal("5.00"),
        total=Decimal("15.80"),
        shipping_address=_address(),
        status=status,
    )


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (OrderStatus.PENDING, OrderStatus.PAID),
        (OrderStatus.PENDING, OrderStatus.CANCELLED),
        (OrderStatus.PAID, OrderStatus.FULFILLED),
        (OrderStatus.PAID, OrderStatus.REFUNDED),
        (OrderStatus.FULFILLED, OrderStatus.REFUNDED),
    ],
)
def test_valid_order_status_transitions(start: OrderStatus, target: OrderStatus) -> None:
    order = _order(start)
    order.transition_to(target)
    assert order.status == target


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (OrderStatus.PENDING, OrderStatus.FULFILLED),
        (OrderStatus.CANCELLED, OrderStatus.PAID),
        (OrderStatus.REFUNDED, OrderStatus.PAID),
        (OrderStatus.FULFILLED, OrderStatus.PENDING),
    ],
)
def test_invalid_order_status_transitions_rejected(start: OrderStatus, target: OrderStatus) -> None:
    order = _order(start)
    with pytest.raises(ValidationError):
        order.transition_to(target)


def test_cart_add_item_merges_quantity_for_same_product() -> None:
    cart = Cart(tenant_id=uuid4(), session_id="s1")
    product_id = uuid4()
    cart.add_item(product_id, 2)
    cart.add_item(product_id, 3)

    assert len(cart.line_items) == 1
    assert cart.line_items[0].quantity == 5


def test_cart_set_item_quantity_zero_removes_item() -> None:
    cart = Cart(tenant_id=uuid4(), session_id="s1")
    product_id = uuid4()
    cart.add_item(product_id, 2)

    cart.set_item_quantity(product_id, 0)

    assert cart.line_items == []


def test_cart_requires_customer_or_session() -> None:
    with pytest.raises(ValidationError):
        Cart(tenant_id=uuid4())


def test_cart_line_item_rejects_non_positive_quantity() -> None:
    with pytest.raises(ValidationError):
        CartLineItem(product_id=uuid4(), quantity=0)
