from typing import Protocol


class ObjectStorage(Protocol):
    async def upload(self, *, key: str, content: bytes, content_type: str) -> str:
        """Uploads an object and returns its publicly-servable URL."""
        ...
