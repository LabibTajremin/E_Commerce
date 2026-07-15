from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.domain.value_objects.money import Money


@dataclass(slots=True)
class SubscriptionPlan:
    name: str
    price: Money
    max_products: int
    max_banners: int
    custom_domain_allowed: bool
    id: UUID = field(default_factory=uuid4)
    stripe_price_id: str | None = None
