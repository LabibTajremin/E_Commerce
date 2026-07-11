from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from src.domain.entities.order import OrderLineItem


@dataclass(frozen=True, slots=True)
class PricingConfig:
    """A single flat tax rate and flat/free-shipping threshold — a real
    multi-jurisdiction tax/shipping-rules engine is out of scope here, see
    docs/decisions/phase6-cart-orders.md. Values are supplied by the caller
    (sourced from Settings at the composition root) rather than hardcoded
    here, so they're configurable per deployment without a code change —
    the domain layer itself stays framework/config-free."""

    tax_rate: Decimal = Decimal("0.08")
    flat_shipping_fee: Decimal = Decimal("5.00")
    free_shipping_threshold: Decimal = Decimal("50.00")


@dataclass(frozen=True, slots=True)
class OrderTotals:
    subtotal: Decimal
    tax: Decimal
    shipping: Decimal
    total: Decimal


_DEFAULT_PRICING_CONFIG = PricingConfig()


def _round(amount: Decimal) -> Decimal:
    return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_totals(
    line_items: list[OrderLineItem], config: PricingConfig = _DEFAULT_PRICING_CONFIG
) -> OrderTotals:
    subtotal = _round(sum((item.line_total for item in line_items), Decimal("0.00")))
    tax = _round(subtotal * config.tax_rate)
    shipping = (
        Decimal("0.00") if subtotal >= config.free_shipping_threshold else config.flat_shipping_fee
    )
    total = _round(subtotal + tax + shipping)
    return OrderTotals(subtotal=subtotal, tax=tax, shipping=shipping, total=total)
