from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.application.interfaces.payment_gateway import PaymentGateway, WebhookEvent
from src.application.interfaces.unit_of_work import UnitOfWork
from src.core.logging import get_logger
from src.domain.entities.order import OrderStatus

logger = get_logger(__name__)

_SUBSCRIPTION_EVENT_TYPES = {"customer.subscription.created", "customer.subscription.updated"}


@dataclass(frozen=True, slots=True)
class ProcessStripeWebhookInput:
    payload: bytes
    signature_header: str


class ProcessStripeWebhookUseCase:
    def __init__(self, payment_gateway: PaymentGateway, uow: UnitOfWork) -> None:
        self._gateway = payment_gateway
        self._uow = uow

    async def execute(self, data: ProcessStripeWebhookInput) -> str:
        event = self._gateway.verify_webhook_signature(data.payload, data.signature_header)

        async with self._uow as uow:
            if await uow.webhook_events.is_processed(event.id):
                logger.info("webhook_replay_ignored", event_id=event.id, event_type=event.type)
                return "already_processed"

            metadata = event.data.get("metadata") or {}
            tenant_id_raw = metadata.get("tenant_id")
            if tenant_id_raw is not None:
                # RLS context isn't set by tenant-resolution middleware for this
                # route (Stripe posts to one global URL) — pin it here from the
                # event's own metadata before touching any tenant-scoped
                # repository, exactly like RegisterTenantOwnerUseCase does for
                # its own "no tenant context yet" bootstrap case.
                await uow.set_tenant_context(UUID(tenant_id_raw))

                if event.type == "checkout.session.completed":
                    await self._handle_checkout_completed(uow, event)
                elif event.type in _SUBSCRIPTION_EVENT_TYPES:
                    await self._handle_subscription_updated(uow, event)
                elif event.type == "customer.subscription.deleted":
                    await self._handle_subscription_deleted(uow, event)
                else:
                    logger.info("webhook_unhandled_event_type", event_type=event.type)
            else:
                # No tenant metadata (an event type we don't act on) — nothing
                # tenant-scoped to touch, just acknowledge it.
                logger.info("webhook_no_tenant_metadata", event_type=event.type)

            await uow.webhook_events.mark_processed(event.id, event.type)
            await uow.commit()

        return "processed"

    async def _handle_checkout_completed(self, uow: UnitOfWork, event: WebhookEvent) -> None:
        metadata = event.data.get("metadata") or {}
        if metadata.get("kind") != "order_payment":
            return

        tenant_id = UUID(metadata["tenant_id"])
        order_id = UUID(metadata["order_id"])
        order = await uow.orders.get_by_id(tenant_id, order_id)
        if order is None:
            logger.warning("webhook_order_not_found", order_id=str(order_id))
            return
        if order.status == OrderStatus.PENDING:
            order.transition_to(OrderStatus.PAID)
            await uow.orders.update(order)

    async def _handle_subscription_updated(self, uow: UnitOfWork, event: WebhookEvent) -> None:
        metadata = event.data.get("metadata") or {}
        tenant_id = UUID(metadata["tenant_id"])

        subscription = await uow.tenant_subscriptions.get_by_tenant(tenant_id)
        if subscription is None:
            logger.warning("webhook_subscription_not_pre_created", tenant_id=str(tenant_id))
            return

        subscription.stripe_customer_id = event.data.get("customer")
        subscription.stripe_subscription_id = event.data.get("id")
        period_end_ts = event.data.get("current_period_end")
        period_end = datetime.fromtimestamp(period_end_ts, tz=UTC) if period_end_ts else None
        subscription.apply_stripe_status(event.data.get("status", ""), period_end)
        await uow.tenant_subscriptions.upsert(subscription)

    async def _handle_subscription_deleted(self, uow: UnitOfWork, event: WebhookEvent) -> None:
        stripe_subscription_id = event.data.get("id")
        if not stripe_subscription_id:
            return
        subscription = await uow.tenant_subscriptions.get_by_stripe_subscription_id(
            stripe_subscription_id
        )
        if subscription is None:
            return
        subscription.apply_stripe_status("canceled", None)
        await uow.tenant_subscriptions.upsert(subscription)
