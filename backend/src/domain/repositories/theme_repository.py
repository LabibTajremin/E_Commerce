from typing import Protocol
from uuid import UUID

from src.domain.entities.theme import Theme


class ThemeRepository(Protocol):
    async def get_by_id(self, theme_id: UUID) -> Theme | None: ...

    async def list(self) -> list[Theme]: ...
