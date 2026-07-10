import stripe

from src.application.interfaces.payment_gateway import WebhookEvent
from src.core.config import settings

stripe.api_key = settings.stripe_secret_key


class StripePaymentGateway:
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
        session = await stripe.checkout.Session.create_async(
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": currency.lower(),
                        "unit_amount": amount_cents,
                        "product_data": {"name": f"Order {order_id}"},
                    },
                    "quantity": 1,
                }
            ],
            metadata={"tenant_id": tenant_id, "order_id": order_id, "kind": "order_payment"},
            success_url=success_url,
            cancel_url=cancel_url,
        )
        url = session.url
        assert url is not None
        return url

    async def create_subscription_checkout_session(
        self,
        *,
        tenant_id: str,
        stripe_price_id: str,
        customer_email: str,
        success_url: str,
        cancel_url: str,
    ) -> str:
        session = await stripe.checkout.Session.create_async(
            mode="subscription",
            line_items=[{"price": stripe_price_id, "quantity": 1}],
            customer_email=customer_email,
            metadata={"tenant_id": tenant_id, "kind": "platform_subscription"},
            subscription_data={"metadata": {"tenant_id": tenant_id}},
            success_url=success_url,
            cancel_url=cancel_url,
        )
        url = session.url
        assert url is not None
        return url

    def verify_webhook_signature(self, payload: bytes, signature_header: str) -> WebhookEvent:
        try:
            event = stripe.Webhook.construct_event(  # type: ignore[no-untyped-call]
                payload, signature_header, settings.stripe_webhook_secret
            )
        except (ValueError, stripe.SignatureVerificationError) as exc:
            raise ValueError("Invalid Stripe webhook signature") from exc
        return WebhookEvent(id=event["id"], type=event["type"], data=event["data"]["object"])
