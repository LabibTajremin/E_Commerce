from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.repositories.sqlalchemy_webhook_event_store import (
    SqlAlchemyWebhookEventStore,
)


async def test_is_processed_false_for_unseen_event(db_session: AsyncSession) -> None:
    store = SqlAlchemyWebhookEventStore(db_session)
    assert await store.is_processed("evt_never_seen") is False


async def test_mark_processed_then_is_processed_true(db_session: AsyncSession) -> None:
    store = SqlAlchemyWebhookEventStore(db_session)
    await store.mark_processed("evt_abc", "checkout.session.completed")
    await db_session.commit()

    assert await store.is_processed("evt_abc") is True


async def test_mark_processed_twice_is_idempotent_no_error(db_session: AsyncSession) -> None:
    """DoD: the idempotency mechanism itself must survive being invoked twice
    for the same event (e.g. two racing webhook deliveries) without raising."""
    store = SqlAlchemyWebhookEventStore(db_session)

    await store.mark_processed("evt_race", "checkout.session.completed")
    await store.mark_processed("evt_race", "checkout.session.completed")  # must not raise
    await db_session.commit()

    assert await store.is_processed("evt_race") is True
