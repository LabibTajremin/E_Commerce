from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.entities.tenant_subscription import SubscriptionStatus, TenantSubscription
from src.domain.exceptions import PlanLimitExceededError
from src.domain.services.plan_limit_policy import PlanLimitPolicy
from src.domain.value_objects.money import Money


def _plan(
    *, max_products: int = 50, max_banners: int = 5, custom_domain_allowed: bool = False
) -> SubscriptionPlan:
    return SubscriptionPlan(
        name="Growth",
        price=Money(Decimal("29.00")),
        max_products=max_products,
        max_banners=max_banners,
        custom_domain_allowed=custom_domain_allowed,
    )


def test_subscription_plan_holds_money_price() -> None:
    plan = SubscriptionPlan(
        name="Growth",
        price=Money(Decimal("29.00")),
        max_products=500,
        max_banners=5,
        custom_domain_allowed=False,
    )
    assert plan.price.amount == Decimal("29.00")


def test_apply_stripe_status_maps_known_statuses() -> None:
    sub = TenantSubscription(tenant_id=uuid4(), plan_id=uuid4())
    period_end = datetime(2026, 8, 1, tzinfo=UTC)

    sub.apply_stripe_status("active", period_end)

    assert sub.status == SubscriptionStatus.ACTIVE
    assert sub.current_period_end == period_end


def test_apply_stripe_status_maps_unpaid_to_past_due() -> None:
    sub = TenantSubscription(tenant_id=uuid4(), plan_id=uuid4())
    sub.apply_stripe_status("unpaid", None)
    assert sub.status == SubscriptionStatus.PAST_DUE


def test_apply_stripe_status_ignores_unknown_status() -> None:
    sub = TenantSubscription(tenant_id=uuid4(), plan_id=uuid4(), status=SubscriptionStatus.ACTIVE)
    sub.apply_stripe_status("some_future_stripe_status", None)
    assert sub.status == SubscriptionStatus.ACTIVE


def test_apply_stripe_status_preserves_period_end_when_not_given() -> None:
    period_end = datetime(2026, 8, 1, tzinfo=UTC)
    sub = TenantSubscription(
        tenant_id=uuid4(), plan_id=uuid4(), current_period_end=period_end
    )
    sub.apply_stripe_status("active", None)
    assert sub.current_period_end == period_end


def test_check_product_limit_allows_below_cap() -> None:
    PlanLimitPolicy.check_product_limit(49, _plan(max_products=50))


def test_check_product_limit_rejects_51st_product_on_50_cap() -> None:
    with pytest.raises(PlanLimitExceededError):
        PlanLimitPolicy.check_product_limit(50, _plan(max_products=50))


def test_check_banner_limit_allows_below_cap() -> None:
    PlanLimitPolicy.check_banner_limit(4, _plan(max_banners=5))


def test_check_banner_limit_rejects_at_cap() -> None:
    with pytest.raises(PlanLimitExceededError):
        PlanLimitPolicy.check_banner_limit(5, _plan(max_banners=5))


def test_check_custom_domain_allowed_passes_when_enabled() -> None:
    PlanLimitPolicy.check_custom_domain_allowed(_plan(custom_domain_allowed=True))


def test_check_custom_domain_allowed_rejects_when_disabled() -> None:
    with pytest.raises(PlanLimitExceededError):
        PlanLimitPolicy.check_custom_domain_allowed(_plan(custom_domain_allowed=False))
