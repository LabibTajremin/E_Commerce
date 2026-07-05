from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.session import async_session_factory


class UnitOfWork:
    """Pins the Postgres RLS tenant setting for the lifetime of one transaction."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    @asynccontextmanager
    async def begin(tenant_id: UUID | None = None) -> AsyncIterator["UnitOfWork"]:
        async with async_session_factory() as session, session.begin():
            if tenant_id is not None:
                # SET has no bind-parameter support over the wire protocol; tenant_id is a
                # UUID instance (not raw client input), so inlining str() is injection-safe.
                await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))
            yield UnitOfWork(session)
