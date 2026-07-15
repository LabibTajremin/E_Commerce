from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class WebhookEvent:
    id: str
    type: str
    data: dict[str, Any]


class PaymentGateway(Protocol):
    async def create_order_checkout_session(
        self,
        *,
        tenant_id: str,
        order_id: str,
        amount_cents: int,
        currency: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Returns the hosted checkout URL for a one-off order payment."""
        ...

    async def create_subscription_checkout_session(
        self,
        *,
        tenant_id: str,
        stripe_price_id: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        """Returns the hosted checkout URL for a platform-billing subscription."""
        ...

    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> WebhookEvent:
        """Raises ValueError on an invalid/forged signature."""
        ...
