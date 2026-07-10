from uuid import UUID

from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.subscription_plan_repository import SubscriptionPlanRepository
from src.domain.repositories.tenant_subscription_repository import TenantSubscriptionRepository


class GetEffectivePlanUseCase:
    def __init__(
        self,
        plan_repository: SubscriptionPlanRepository,
        subscription_repository: TenantSubscriptionRepository,
    ) -> None:
        self._plans = plan_repository
        self._subscriptions = subscription_repository

    async def execute(self, tenant_id: UUID) -> SubscriptionPlan:
        subscription = await self._subscriptions.get_by_tenant(tenant_id)
        if subscription is not None:
            plan = await self._plans.get_by_id(subscription.plan_id)
            if plan is not None:
                return plan

        # No explicit subscription yet (e.g. a tenant that just registered and
        # hasn't picked a plan) — default to the cheapest configured plan.
        plans = await self._plans.list()
        if not plans:
            raise EntityNotFoundError("SubscriptionPlan", "no plans configured")
        return min(plans, key=lambda p: p.price.amount)
