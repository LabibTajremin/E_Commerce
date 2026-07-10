from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.value_objects.money import Money
from src.infrastructure.db.models.subscription_plan import SubscriptionPlanModel


class SqlAlchemySubscriptionPlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: SubscriptionPlanModel) -> SubscriptionPlan:
        return SubscriptionPlan(
            id=model.id,
            name=model.name,
            price=Money(model.price),
            max_products=model.max_products,
            max_banners=model.max_banners,
            custom_domain_allowed=model.custom_domain_allowed,
            stripe_price_id=model.stripe_price_id,
        )

    async def get_by_id(self, plan_id: UUID) -> SubscriptionPlan | None:
        model = await self._session.get(SubscriptionPlanModel, plan_id)
        return self._to_entity(model) if model else None

    async def list(self) -> list[SubscriptionPlan]:
        result = await self._session.execute(
            select(SubscriptionPlanModel).order_by(SubscriptionPlanModel.price)
        )
        return [self._to_entity(m) for m in result.scalars().all()]
