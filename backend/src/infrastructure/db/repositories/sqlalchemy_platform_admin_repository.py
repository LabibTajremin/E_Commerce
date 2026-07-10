from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.platform_admin import PlatformAdmin
from src.domain.value_objects.email import Email
from src.infrastructure.db.models.platform_admin import PlatformAdminModel


class SqlAlchemyPlatformAdminRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: PlatformAdminModel) -> PlatformAdmin:
        return PlatformAdmin(
            id=model.id,
            email=Email(model.email),
            hashed_password=model.hashed_password,
            created_at=model.created_at,
        )

    async def get_by_id(self, platform_admin_id: UUID) -> PlatformAdmin | None:
        result = await self._session.execute(
            select(PlatformAdminModel).where(PlatformAdminModel.id == platform_admin_id)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, email: str) -> PlatformAdmin | None:
        result = await self._session.execute(
            select(PlatformAdminModel).where(PlatformAdminModel.email == email.strip().lower())
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def add(self, platform_admin: PlatformAdmin) -> PlatformAdmin:
        model = PlatformAdminModel(
            id=platform_admin.id,
            email=str(platform_admin.email),
            hashed_password=platform_admin.hashed_password,
            created_at=platform_admin.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)
