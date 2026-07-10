from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.use_cases.billing.create_order_checkout_session import (
    CreateOrderCheckoutSessionInput,
    CreateOrderCheckoutSessionUseCase,
)
from src.application.use_cases.billing.create_subscription_checkout import (
    CreateSubscriptionCheckoutInput,
    CreateSubscriptionCheckoutUseCase,
)
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
from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.value_objects.address import Address
from src.domain.value_objects.money import Money
from tests.unit.application.fakes import (
    FakeCartRepository,
    FakeCategoryRepository,
    FakeCheckoutUnitOfWork,
    FakeCustomerRepository,
    FakeOrderRepository,
    FakePaymentGateway,
    FakeProductRepository,
    FakeTenantSubscriptionRepository,
    unlimited_plan_use_case,
)


def _address() -> Address:
    return Address(
        line1="1 Main St", city="Metropolis", state="CA", postal_code="90210", country="US"
    )


async def test_create_order_checkout_session_uses_order_total_in_cents() -> None:
    tenant_id = uuid4()
    products = FakeProductRepository()
    customers = FakeCustomerRepository()
    carts = FakeCartRepository()
    orders = FakeOrderRepository()
    categories = FakeCategoryRepository()
    gateway = FakePaymentGateway()

    customer = await RegisterCustomerUseCase(customers).execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )
    product = await CreateProductUseCase(products, categories, unlimited_plan_use_case()).execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("10.00"), stock_qty=5)
    )
    cart = Cart(tenant_id=tenant_id, customer_id=customer.id)
    cart.add_item(product.id, 1)
    await carts.upsert(cart)
    uow = FakeCheckoutUnitOfWork(products, customers, carts, orders)
    order = await CheckoutUseCase(uow).execute(
        CheckoutInput(tenant_id=tenant_id, customer_id=customer.id, shipping_address=_address())
    )

    url = await CreateOrderCheckoutSessionUseCase(orders, gateway).execute(
        CreateOrderCheckoutSessionInput(
            tenant_id=tenant_id,
            order_id=order.id,
            success_url="https://shop.test/success",
            cancel_url="https://shop.test/cancel",
        )
    )

    assert url.startswith("https://checkout.stripe.test/")
    assert gateway.checkout_calls[0]["amount_cents"] == int(order.total * 100)


async def test_create_order_checkout_session_rejects_already_paid_order() -> None:
    orders = FakeOrderRepository()
    gateway = FakePaymentGateway()

    with pytest.raises(EntityNotFoundError):
        await CreateOrderCheckoutSessionUseCase(orders, gateway).execute(
            CreateOrderCheckoutSessionInput(
                tenant_id=uuid4(),
                order_id=uuid4(),
                success_url="https://shop.test/success",
                cancel_url="https://shop.test/cancel",
            )
        )


async def test_create_subscription_checkout_requires_stripe_price_configured() -> None:
    plans = _FakePlanRepo([SubscriptionPlan(
        name="Growth", price=Money(Decimal("29")), max_products=500, max_banners=5,
        custom_domain_allowed=False, stripe_price_id=None,
    )])
    subscriptions = FakeTenantSubscriptionRepository()
    gateway = FakePaymentGateway()

    with pytest.raises(ValidationError):
        await CreateSubscriptionCheckoutUseCase(plans, subscriptions, gateway).execute(
            CreateSubscriptionCheckoutInput(
                tenant_id=uuid4(),
                plan_id=plans.plans[0].id,
                owner_email="owner@acme.com",
                success_url="https://platform.test/success",
                cancel_url="https://platform.test/cancel",
            )
        )


async def test_create_subscription_checkout_pre_creates_subscription_record() -> None:
    plan = SubscriptionPlan(
        name="Growth", price=Money(Decimal("29")), max_products=500, max_banners=5,
        custom_domain_allowed=False, stripe_price_id="price_123",
    )
    plans = _FakePlanRepo([plan])
    subscriptions = FakeTenantSubscriptionRepository()
    gateway = FakePaymentGateway()
    tenant_id = uuid4()

    url = await CreateSubscriptionCheckoutUseCase(plans, subscriptions, gateway).execute(
        CreateSubscriptionCheckoutInput(
            tenant_id=tenant_id,
            plan_id=plan.id,
            owner_email="owner@acme.com",
            success_url="https://platform.test/success",
            cancel_url="https://platform.test/cancel",
        )
    )

    assert url.startswith("https://checkout.stripe.test/")
    pre_created = await subscriptions.get_by_tenant(tenant_id)
    assert pre_created is not None
    assert pre_created.plan_id == plan.id


class _FakePlanRepo:
    def __init__(self, plans: list[SubscriptionPlan]) -> None:
        self.plans = plans

    async def get_by_id(self, plan_id):  # type: ignore[no-untyped-def]
        return next((p for p in self.plans if p.id == plan_id), None)

    async def list(self):  # type: ignore[no-untyped-def]
        return self.plans
