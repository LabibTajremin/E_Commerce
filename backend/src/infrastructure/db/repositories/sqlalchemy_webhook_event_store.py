from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.models.webhook_event import ProcessedWebhookEventModel


class SqlAlchemyWebhookEventStore:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_processed(self, event_id: str) -> bool:
        model = await self._session.get(ProcessedWebhookEventModel, event_id)
        return model is not None

    async def mark_processed(self, event_id: str, event_type: str) -> None:
        # ON CONFLICT DO NOTHING: if two webhook deliveries for the same event
        # race each other, both may pass is_processed()=False before either
        # commits — the primary key + upsert makes the second insert a no-op
        # instead of raising, keeping "mark processed" itself idempotent.
        stmt = (
            pg_insert(ProcessedWebhookEventModel)
            .values(event_id=event_id, event_type=event_type)
            .on_conflict_do_nothing(index_elements=["event_id"])
        )
        await self._session.execute(stmt)
        await self._session.flush()
