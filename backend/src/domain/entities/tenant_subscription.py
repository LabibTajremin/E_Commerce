from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4


class SubscriptionStatus(StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


@dataclass(slots=True)
class TenantSubscription:
    tenant_id: UUID
    plan_id: UUID
    id: UUID = field(default_factory=uuid4)
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    status: SubscriptionStatus = SubscriptionStatus.TRIALING
    current_period_end: datetime | None = None

    def apply_stripe_status(self, stripe_status: str, current_period_end: datetime | None) -> None:
        mapping = {
            "trialing": SubscriptionStatus.TRIALING,
            "active": SubscriptionStatus.ACTIVE,
            "past_due": SubscriptionStatus.PAST_DUE,
            "unpaid": SubscriptionStatus.PAST_DUE,
            "canceled": SubscriptionStatus.CANCELED,
            "incomplete_expired": SubscriptionStatus.CANCELED,
        }
        self.status = mapping.get(stripe_status, self.status)
        if current_period_end is not None:
            self.current_period_end = current_period_end
