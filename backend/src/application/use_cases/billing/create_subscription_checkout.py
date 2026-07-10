from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.payment_gateway import PaymentGateway
from src.domain.entities.tenant_subscription import TenantSubscription
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.repositories.subscription_plan_repository import SubscriptionPlanRepository
from src.domain.repositories.tenant_subscription_repository import TenantSubscriptionRepository


@dataclass(frozen=True, slots=True)
class CreateSubscriptionCheckoutInput:
    tenant_id: UUID
    plan_id: UUID
    owner_email: str
    success_url: str
    cancel_url: str


class CreateSubscriptionCheckoutUseCase:
    def __init__(
        self,
        plan_repository: SubscriptionPlanRepository,
        tenant_subscription_repository: TenantSubscriptionRepository,
        payment_gateway: PaymentGateway,
    ) -> None:
        self._plans = plan_repository
        self._subscriptions = tenant_subscription_repository
        self._gateway = payment_gateway

    async def execute(self, data: CreateSubscriptionCheckoutInput) -> str:
        plan = await self._plans.get_by_id(data.plan_id)
        if plan is None:
            raise EntityNotFoundError("SubscriptionPlan", data.plan_id)
        if plan.stripe_price_id is None:
            raise ValidationError(f"Plan {plan.name!r} has no Stripe price configured")

        # Pre-create/point the tenant's subscription record at this plan so the
        # webhook (which only carries the Stripe subscription/customer IDs and
        # status, not our plan_id) has a row to update rather than needing a
        # reverse stripe_price_id -> plan_id lookup.
        existing = await self._subscriptions.get_by_tenant(data.tenant_id)
        subscription = existing or TenantSubscription(tenant_id=data.tenant_id, plan_id=plan.id)
        subscription.plan_id = plan.id
        await self._subscriptions.upsert(subscription)

        return await self._gateway.create_subscription_checkout_session(
            tenant_id=str(data.tenant_id),
            stripe_price_id=plan.stripe_price_id,
            customer_email=data.owner_email,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
