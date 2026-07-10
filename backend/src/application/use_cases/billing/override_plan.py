from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.domain.entities.tenant_subscription import SubscriptionStatus, TenantSubscription
from src.domain.exceptions import EntityNotFoundError


@dataclass(frozen=True, slots=True)
class OverridePlanInput:
    tenant_id: UUID
    plan_id: UUID


class OverridePlanUseCase:
    """Superadmin action: force a tenant onto a given plan regardless of
    Stripe subscription state, e.g. comping an account or fixing billing
    disputes."""

    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, data: OverridePlanInput) -> TenantSubscription:
        async with self._uow as uow:
            if await uow.tenants.get_by_id(data.tenant_id) is None:
                raise EntityNotFoundError("Tenant", data.tenant_id)
            if await uow.subscription_plans.get_by_id(data.plan_id) is None:
                raise EntityNotFoundError("SubscriptionPlan", data.plan_id)

            await uow.set_tenant_context(data.tenant_id)
            existing = await uow.tenant_subscriptions.get_by_tenant(data.tenant_id)
            if existing is not None:
                existing.plan_id = data.plan_id
                subscription = existing
            else:
                subscription = TenantSubscription(
                    tenant_id=data.tenant_id,
                    plan_id=data.plan_id,
                    status=SubscriptionStatus.ACTIVE,
                )

            subscription = await uow.tenant_subscriptions.upsert(subscription)
            await uow.commit()

        return subscription
