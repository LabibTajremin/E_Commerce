from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.admin_user import AdminRole, AdminUser, AdminUserStatus
from src.domain.value_objects.email import Email
from src.infrastructure.db.models.admin_user import AdminUserModel


class SqlAlchemyAdminUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: AdminUserModel) -> AdminUser:
        return AdminUser(
            id=model.id,
            tenant_id=model.tenant_id,
            email=Email(model.email),
            hashed_password=model.hashed_password,
            role=AdminRole(model.role),
            status=AdminUserStatus(model.status),
            created_at=model.created_at,
        )

    async def get_by_id(self, tenant_id: UUID, user_id: UUID) -> AdminUser | None:
        result = await self._session.execute(
            select(AdminUserModel).where(
                AdminUserModel.id == user_id, AdminUserModel.tenant_id == tenant_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_email(self, tenant_id: UUID, email: str) -> AdminUser | None:
        result = await self._session.execute(
            select(AdminUserModel).where(
                AdminUserModel.tenant_id == tenant_id,
                AdminUserModel.email == email.strip().lower(),
            )
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def add(self, admin_user: AdminUser) -> AdminUser:
        model = AdminUserModel(
            id=admin_user.id,
            tenant_id=admin_user.tenant_id,
            email=str(admin_user.email),
            hashed_password=admin_user.hashed_password,
            role=admin_user.role.value,
            status=admin_user.status.value,
            created_at=admin_user.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, admin_user: AdminUser) -> AdminUser:
        result = await self._session.execute(
            select(AdminUserModel).where(
                AdminUserModel.id == admin_user.id, AdminUserModel.tenant_id == admin_user.tenant_id
            )
        )
        model = result.scalar_one_or_none()
        if model is None:
            raise ValueError(f"AdminUser not found: {admin_user.id}")
        model.hashed_password = admin_user.hashed_password
        model.role = admin_user.role.value
        model.status = admin_user.status.value
        await self._session.flush()
        return self._to_entity(model)
