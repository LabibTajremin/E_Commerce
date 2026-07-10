from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.domain.entities.order import OrderLineItem

# v1 simplification: a single flat tax rate and flat/free-shipping threshold.
# A real multi-jurisdiction tax/shipping-rules engine is out of scope here —
# see docs/decisions/phase6-cart-orders.md.
TAX_RATE = Decimal("0.08")
FLAT_SHIPPING_FEE = Decimal("5.00")
FREE_SHIPPING_THRESHOLD = Decimal("50.00")


@dataclass(frozen=True, slots=True)
class OrderTotals:
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total: Decimal


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_totals(line_items: list[OrderLineItem]) -> OrderTotals:
    subtotal = _round(sum((item.line_total for item in line_items), Decimal("0.00")))
    tax = _round(subtotal * TAX_RATE)
    shipping = Decimal("0.00") if subtotal >= FREE_SHIPPING_THRESHOLD else FLAT_SHIPPING_FEE
    total = _round(subtotal + tax + shipping)
    return OrderTotals(subtotal=subtotal, tax=tax, shipping=shipping, total=total)
