from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.entities.order import Order, OrderLineItem
from src.domain.exceptions import EntityNotFoundError, OutOfStockError, ValidationError
from src.domain.services.pricing import PricingConfig, calculate_totals
from src.domain.value_objects.address import Address


@dataclass(frozen=True, slots=True)
class CheckoutInput:
    tenant_id: UUID
    customer_id: UUID
    shipping_address: Address


class CheckoutUseCase:
    def __init__(self, uow: UnitOfWork, pricing_config: PricingConfig | None = None) -> None:
        self._uow = uow
        self._pricing_config = pricing_config or PricingConfig()

    async def execute(self, data: CheckoutInput) -> Order:
        async with self._uow as uow:
            cart = await uow.carts.get_by_customer(data.tenant_id, data.customer_id)
            if cart is None or not cart.line_items:
                raise ValidationError("Cart is empty")

            order_line_items: list[OrderLineItem] = []
            for item in cart.line_items:
                # Row-locked for the rest of this transaction: a concurrent checkout
                # on the same product blocks here until this one commits or rolls
                # back, then re-reads the post-decrement stock_qty — this is what
                # makes oversell impossible under concurrent checkouts.
                product = await uow.products.get_by_id_for_update(data.tenant_id, item.product_id)
                if product is None:
                    raise EntityNotFoundError("Product", item.product_id)
                if product.stock_qty < item.quantity:
                    raise OutOfStockError(item.product_id, item.quantity, product.stock_qty)

                product.adjust_stock(-item.quantity)
                await uow.products.update(product)

                order_line_items.append(
                    OrderLineItem(
                        product_id=product.id,
                        product_name=product.name,
                        unit_price=product.price,
                        quantity=item.quantity,
                    )
                )

            totals = calculate_totals(order_line_items, self._pricing_config)
            order = Order(
                tenant_id=data.tenant_id,
                customer_id=data.customer_id,
                line_items=order_line_items,
                subtotal=totals.subtotal,
                tax=totals.tax,
                shipping=totals.shipping,
                total=totals.total,
                shipping_address=data.shipping_address,
            )
            created_order = await uow.orders.add(order)

            cart.clear()
            await uow.carts.upsert(cart)

            await uow.commit()

        return created_order
