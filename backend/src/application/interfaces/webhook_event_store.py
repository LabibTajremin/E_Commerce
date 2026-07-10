from typing import Protocol


class WebhookEventStore(Protocol):
    async def is_processed(self, event_id: str) -> bool: ...

    async def mark_processed(self, event_id: str, event_type: str) -> None: ...
