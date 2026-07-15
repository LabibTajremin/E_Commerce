from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.tenant_subscription import SubscriptionStatus, TenantSubscription
from src.infrastructure.db.models.tenant_subscription import TenantSubscriptionModel


class SqlAlchemyTenantSubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: TenantSubscriptionModel) -> TenantSubscription:
        return TenantSubscription(
            id=model.id,
            tenant_id=model.tenant_id,
            plan_id=model.plan_id,
            stripe_customer_id=model.stripe_customer_id,
            stripe_subscription_id=model.stripe_subscription_id,
            status=SubscriptionStatus(model.status),
            current_period_end=model.current_period_end,
        )

    async def get_by_tenant(self, tenant_id: UUID) -> TenantSubscription | None:
        result = await self._session.execute(
            select(TenantSubscriptionModel).where(TenantSubscriptionModel.tenant_id == tenant_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> TenantSubscription | None:
        result = await self._session.execute(
            select(TenantSubscriptionModel).where(
                TenantSubscriptionModel.stripe_subscription_id == stripe_subscription_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def upsert(self, subscription: TenantSubscription) -> TenantSubscription:
        result = await self._session.execute(
            select(TenantSubscriptionModel).where(
                TenantSubscriptionModel.tenant_id == subscription.tenant_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            model = TenantSubscriptionModel(id=subscription.id, tenant_id=subscription.tenant_id)
            self._session.add(model)

        model.plan_id = subscription.plan_id
        model.stripe_customer_id = subscription.stripe_customer_id
        model.stripe_subscription_id = subscription.stripe_subscription_id
        model.status = subscription.status.value
        model.current_period_end = subscription.current_period_end

        await self._session.flush()
        return self._to_entity(model)
