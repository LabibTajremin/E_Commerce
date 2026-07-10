from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.application.interfaces.payment_gateway import WebhookEvent
from src.application.use_cases.billing.process_stripe_webhook import (
    ProcessStripeWebhookInput,
    ProcessStripeWebhookUseCase,
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
from src.domain.entities.order import OrderStatus
from src.domain.entities.tenant_subscription import SubscriptionStatus, TenantSubscription
from src.domain.value_objects.address import Address
from tests.unit.application.fakes import (
    FakeCartRepository,
    FakeCategoryRepository,
    FakeCheckoutUnitOfWork,
    FakeCustomerRepository,
    FakeOrderRepository,
    FakePaymentGateway,
    FakeProductRepository,
    FakeTenantSubscriptionRepository,
    FakeWebhookEventStore,
)


def _address() -> Address:
    return Address(
        line1="1 Main St", city="Metropolis", state="CA", postal_code="90210", country="US"
    )


def _order_payment_event(event_id: str, tenant_id: UUID, order_id: UUID) -> WebhookEvent:
    return WebhookEvent(
        id=event_id,
        type="checkout.session.completed",
        data={
            "metadata": {
                "tenant_id": str(tenant_id),
                "order_id": str(order_id),
                "kind": "order_payment",
            }
        },
    )


async def _checked_out_order(
    tenant_id: UUID,
    products: FakeProductRepository,
    customers: FakeCustomerRepository,
    carts: FakeCartRepository,
    orders: FakeOrderRepository,
):  # type: ignore[no-untyped-def]
    categories = FakeCategoryRepository()
    customer = await RegisterCustomerUseCase(customers).execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email="jane@example.com", password="hunter22!!", name="Jane"
        )
    )
    product = await CreateProductUseCase(products, categories).execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("10.00"), stock_qty=5)
    )
    cart = Cart(tenant_id=tenant_id, customer_id=customer.id)
    cart.add_item(product.id, 1)
    await carts.upsert(cart)
    checkout_uow = FakeCheckoutUnitOfWork(products, customers, carts, orders)
    return await CheckoutUseCase(checkout_uow).execute(
        CheckoutInput(tenant_id=tenant_id, customer_id=customer.id, shipping_address=_address())
    )


async def test_checkout_completed_webhook_marks_order_paid() -> None:
    tenant_id = uuid4()
    products, customers, carts, orders = (
        FakeProductRepository(),
        FakeCustomerRepository(),
        FakeCartRepository(),
        FakeOrderRepository(),
    )
    order = await _checked_out_order(tenant_id, products, customers, carts, orders)

    event = _order_payment_event("evt_1", tenant_id, order.id)
    gateway = FakePaymentGateway(webhook_event=event)
    uow = FakeCheckoutUnitOfWork(products, customers, carts, orders)

    result = await ProcessStripeWebhookUseCase(gateway, uow).execute(
        ProcessStripeWebhookInput(payload=b"{}", signature_header="valid-signature")
    )

    assert result == "processed"
    updated_order = await orders.get_by_id(tenant_id, order.id)
    assert updated_order is not None
    assert updated_order.status == OrderStatus.PAID


async def test_replaying_the_same_event_twice_has_no_duplicate_side_effects() -> None:
    """DoD: webhook handler is idempotent — replaying the same event twice has
    no duplicate side effects."""
    tenant_id = uuid4()
    products, customers, carts, orders = (
        FakeProductRepository(),
        FakeCustomerRepository(),
        FakeCartRepository(),
        FakeOrderRepository(),
    )
    order = await _checked_out_order(tenant_id, products, customers, carts, orders)

    event = _order_payment_event("evt_replay", tenant_id, order.id)
    gateway = FakePaymentGateway(webhook_event=event)
    webhook_events = FakeWebhookEventStore()
    uow = FakeCheckoutUnitOfWork(products, customers, carts, orders, webhook_events=webhook_events)

    first_result = await ProcessStripeWebhookUseCase(gateway, uow).execute(
        ProcessStripeWebhookInput(payload=b"{}", signature_header="valid-signature")
    )
    # Replay: same event, delivered a second time (Stripe's at-least-once guarantee).
    second_result = await ProcessStripeWebhookUseCase(gateway, uow).execute(
        ProcessStripeWebhookInput(payload=b"{}", signature_header="valid-signature")
    )

    assert first_result == "processed"
    assert second_result == "already_processed"

    order_after_replay = await orders.get_by_id(tenant_id, order.id)
    assert order_after_replay is not None
    assert order_after_replay.status == OrderStatus.PAID  # not double-transitioned or errored


async def test_replaying_event_does_not_error_on_already_transitioned_order() -> None:
    """A stricter version of the idempotency guarantee: even if somehow called
    twice on an order already in PAID, the handler must not raise (it no-ops
    instead of calling transition_to on a non-PENDING order)."""
    tenant_id = uuid4()
    products, customers, carts, orders = (
        FakeProductRepository(),
        FakeCustomerRepository(),
        FakeCartRepository(),
        FakeOrderRepository(),
    )
    order = await _checked_out_order(tenant_id, products, customers, carts, orders)
    order.transition_to(OrderStatus.PAID)
    await orders.update(order)

    event = _order_payment_event("evt_already_paid", tenant_id, order.id)
    gateway = FakePaymentGateway(webhook_event=event)
    uow = FakeCheckoutUnitOfWork(products, customers, carts, orders)

    result = await ProcessStripeWebhookUseCase(gateway, uow).execute(
        ProcessStripeWebhookInput(payload=b"{}", signature_header="valid-signature")
    )

    assert result == "processed"
    unchanged_order = await orders.get_by_id(tenant_id, order.id)
    assert unchanged_order is not None
    assert unchanged_order.status == OrderStatus.PAID


async def test_invalid_signature_rejected() -> None:
    gateway = FakePaymentGateway(
        webhook_event=WebhookEvent(id="evt_x", type="checkout.session.completed", data={})
    )
    uow = FakeCheckoutUnitOfWork(
        FakeProductRepository(),
        FakeCustomerRepository(),
        FakeCartRepository(),
        FakeOrderRepository(),
    )

    with pytest.raises(ValueError):
        await ProcessStripeWebhookUseCase(gateway, uow).execute(
            ProcessStripeWebhookInput(payload=b"{}", signature_header="forged-signature")
        )


async def test_subscription_updated_webhook_syncs_status_and_period() -> None:
    tenant_id = uuid4()
    plan_id = uuid4()
    subscriptions = FakeTenantSubscriptionRepository()
    await subscriptions.upsert(TenantSubscription(tenant_id=tenant_id, plan_id=plan_id))

    event = WebhookEvent(
        id="evt_sub_1",
        type="customer.subscription.updated",
        data={
            "id": "sub_123",
            "customer": "cus_123",
            "status": "active",
            "current_period_end": 1893456000,
            "metadata": {"tenant_id": str(tenant_id)},
        },
    )
    gateway = FakePaymentGateway(webhook_event=event)
    uow = FakeCheckoutUnitOfWork(
        FakeProductRepository(),
        FakeCustomerRepository(),
        FakeCartRepository(),
        FakeOrderRepository(),
        tenant_subscriptions=subscriptions,
    )

    await ProcessStripeWebhookUseCase(gateway, uow).execute(
        ProcessStripeWebhookInput(payload=b"{}", signature_header="valid-signature")
    )

    updated = await subscriptions.get_by_tenant(tenant_id)
    assert updated is not None
    assert updated.status == SubscriptionStatus.ACTIVE
    assert updated.stripe_subscription_id == "sub_123"


async def test_subscription_deleted_webhook_marks_canceled() -> None:
    tenant_id = uuid4()
    subscriptions = FakeTenantSubscriptionRepository()
    sub = TenantSubscription(
        tenant_id=tenant_id,
        plan_id=uuid4(),
        stripe_subscription_id="sub_to_cancel",
        status=SubscriptionStatus.ACTIVE,
    )
    await subscriptions.upsert(sub)

    event = WebhookEvent(
        id="evt_sub_deleted",
        type="customer.subscription.deleted",
        data={"id": "sub_to_cancel", "metadata": {"tenant_id": str(tenant_id)}},
    )
    gateway = FakePaymentGateway(webhook_event=event)
    uow = FakeCheckoutUnitOfWork(
        FakeProductRepository(),
        FakeCustomerRepository(),
        FakeCartRepository(),
        FakeOrderRepository(),
        tenant_subscriptions=subscriptions,
    )

    await ProcessStripeWebhookUseCase(gateway, uow).execute(
        ProcessStripeWebhookInput(payload=b"{}", signature_header="valid-signature")
    )

    updated = await subscriptions.get_by_tenant(tenant_id)
    assert updated is not None
    assert updated.status == SubscriptionStatus.CANCELED
