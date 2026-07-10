from typing import Protocol
from uuid import UUID

from src.domain.entities.tenant_subscription import TenantSubscription


class TenantSubscriptionRepository(Protocol):
    async def get_by_tenant(self, tenant_id: UUID) -> TenantSubscription | None: ...

    async def get_by_stripe_subscription_id(
        self, stripe_subscription_id: str
    ) -> TenantSubscription | None: ...

    async def upsert(self, subscription: TenantSubscription) -> TenantSubscription: ...
