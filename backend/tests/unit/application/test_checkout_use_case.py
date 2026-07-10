from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.customers.register_customer import (
    RegisterCustomerInput,
    RegisterCustomerUseCase,
)
from src.application.use_cases.orders.checkout import CheckoutInput, CheckoutUseCase
from src.application.use_cases.products.create_product import (
    CreateProductInput,
    CreateProductUseCase,
)
from src.domain.entities.cart import Cart
from src.domain.exceptions import EntityNotFoundError, OutOfStockError, ValidationError
from src.domain.value_objects.address import Address
from tests.unit.application.fakes import (
    FakeCartRepository,
    FakeCategoryRepository,
    FakeCheckoutUnitOfWork,
    FakeCustomerRepository,
    FakeOrderRepository,
    FakeProductRepository,
)


def _address() -> Address:
    return Address(
        line1="1 Main St", city="Metropolis", state="CA", postal_code="90210", country="US"
    )


async def _setup(
    tenant_id: UUID,
) -> tuple[
    FakeProductRepository,
    FakeCustomerRepository,
    FakeCartRepository,
    FakeOrderRepository,
    object,
    object,
]:
    products = FakeProductRepository()
    customers = FakeCustomerRepository()
    carts = FakeCartRepository()
    orders = FakeOrderRepository()
    categories = FakeCategoryRepository()

    customer = await RegisterCustomerUseCase(customers).execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )
    product = await CreateProductUseCase(products, categories).execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("10.00"), stock_qty=5)
    )
    return products, customers, carts, orders, customer, product


async def test_checkout_decrements_stock_and_creates_order() -> None:
    tenant_id = uuid4()
    products, customers, carts, orders, customer, product = await _setup(tenant_id)
    cart = Cart(tenant_id=tenant_id, customer_id=customer.id)
    cart.add_item(product.id, 2)
    await carts.upsert(cart)

    uow = FakeCheckoutUnitOfWork(products, customers, carts, orders)
    order = await CheckoutUseCase(uow).execute(
        CheckoutInput(tenant_id=tenant_id, customer_id=customer.id, shipping_address=_address())
    )

    assert order.line_items[0].quantity == 2
    assert order.subtotal == Decimal("20.00")
    updated_product = await products.get_by_id(tenant_id, product.id)
    assert updated_product is not None
    assert updated_product.stock_qty == 3
    assert uow.committed is True

    # Cart is cleared after checkout.
    remaining_cart = await carts.get_by_customer(tenant_id, customer.id)
    assert remaining_cart is not None
    assert remaining_cart.line_items == []


async def test_checkout_rejects_empty_cart() -> None:
    tenant_id = uuid4()
    products, customers, carts, orders, customer, _ = await _setup(tenant_id)
    uow = FakeCheckoutUnitOfWork(products, customers, carts, orders)

    with pytest.raises(ValidationError):
        await CheckoutUseCase(uow).execute(
            CheckoutInput(tenant_id=tenant_id, customer_id=customer.id, shipping_address=_address())
        )


async def test_checkout_rejects_insufficient_stock() -> None:
    tenant_id = uuid4()
    products, customers, carts, orders, customer, product = await _setup(tenant_id)
    cart = Cart(tenant_id=tenant_id, customer_id=customer.id)
    cart.add_item(product.id, 999)
    await carts.upsert(cart)
    uow = FakeCheckoutUnitOfWork(products, customers, carts, orders)

    with pytest.raises(OutOfStockError):
        await CheckoutUseCase(uow).execute(
            CheckoutInput(tenant_id=tenant_id, customer_id=customer.id, shipping_address=_address())
        )


async def test_checkout_rejects_deleted_product_in_cart() -> None:
    tenant_id = uuid4()
    products, customers, carts, orders, customer, product = await _setup(tenant_id)
    cart = Cart(tenant_id=tenant_id, customer_id=customer.id)
    cart.add_item(product.id, 1)
    await carts.upsert(cart)
    await products.delete(tenant_id, product.id)
    uow = FakeCheckoutUnitOfWork(products, customers, carts, orders)

    with pytest.raises(EntityNotFoundError):
        await CheckoutUseCase(uow).execute(
            CheckoutInput(tenant_id=tenant_id, customer_id=customer.id, shipping_address=_address())
        )
