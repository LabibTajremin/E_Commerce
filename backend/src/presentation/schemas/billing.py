from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.application.use_cases.billing.get_tenant_usage import TenantUsage
from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.entities.tenant_subscription import TenantSubscription


class SubscriptionPlanResponse(BaseModel):
    id: UUID
    name: str
    price: Decimal
    max_products: int
    max_banners: int
    custom_domain_allowed: bool

    @classmethod
    def from_entity(cls, plan: SubscriptionPlan) -> "SubscriptionPlanResponse":
        return cls(
            id=plan.id,
            name=plan.name,
            price=plan.price.amount,
            max_products=plan.max_products,
            max_banners=plan.max_banners,
            custom_domain_allowed=plan.custom_domain_allowed,
        )


class TenantSubscriptionResponse(BaseModel):
    plan_id: UUID
    status: str
    current_period_end: str | None

    @classmethod
    def from_entity(cls, subscription: TenantSubscription) -> "TenantSubscriptionResponse":
        return cls(
            plan_id=subscription.plan_id,
            status=subscription.status.value,
            current_period_end=(
                subscription.current_period_end.isoformat()
                if subscription.current_period_end
                else None
            ),
        )


class TenantUsageResponse(BaseModel):
    tenant_id: UUID
    plan: SubscriptionPlanResponse
    product_count: int
    banner_count: int

    @classmethod
    def from_usage(cls, usage: TenantUsage) -> "TenantUsageResponse":
        return cls(
            tenant_id=usage.tenant_id,
            plan=SubscriptionPlanResponse.from_entity(usage.plan),
            product_count=usage.product_count,
            banner_count=usage.banner_count,
        )


class PlanOverrideRequest(BaseModel):
    plan_id: UUID


class SubscribeRequest(BaseModel):
    plan_id: UUID
    success_url: str
    cancel_url: str


class CheckoutUrlResponse(BaseModel):
    checkout_url: str


class PayOrderRequest(BaseModel):
    success_url: str = Field(min_length=1)
    cancel_url: str = Field(min_length=1)
