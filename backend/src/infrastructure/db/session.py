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
    return create_async_engine(database_url or settings.database_url, pool_pre_ping=True)


engine = create_engine()
async_session_factory = async_sessionmaker(engine, expire_on_commit=False, autoflush=False)


@asynccontextmanager
async def get_session() -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        yield session
