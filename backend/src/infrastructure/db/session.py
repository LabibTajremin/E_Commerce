from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.core.config import settings


class Base(DeclarativeBase):
    pass


def create_engine(database_url: str | None = None) -> AsyncEngine:
    return create_async_engine(
        database_url or settings.database_url,
        pool_pre_ping=True,
        # Disables asyncpg's server-side prepared-statement cache. Required
        # when DATABASE_URL points at a transaction-mode PgBouncer/pooler
        # (e.g. Neon's pooled connection string, used on serverless
        # deployments where every invocation is a fresh connection) — those
        # poolers can hand the same physical connection to unrelated
        # transactions, and asyncpg's cached prepared statements silently
        # collide across them (DuplicatePreparedStatementError) otherwise.
        # A harmless no-op against a direct (non-pooled) connection.
        connect_args={"statement_cache_size": 0},
    )


engine = create_engine()
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
