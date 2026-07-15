from typing import Protocol
from uuid import UUID

from src.domain.entities.subscription_plan import SubscriptionPlan


class SubscriptionPlanRepository(Protocol):
    async def get_by_id(self, plan_id: UUID) -> SubscriptionPlan | None: ...

    async def list(self) -> list[SubscriptionPlan]: ...
