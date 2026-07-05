from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.repositories.tenant_repository import TenantRepository
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.infrastructure.db.session import get_session


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with get_session() as session:
        yield session


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_tenant_repository(session: DbSession) -> TenantRepository:
    return SqlAlchemyTenantRepository(session)


TenantRepositoryDep = Annotated[TenantRepository, Depends(get_tenant_repository)]
