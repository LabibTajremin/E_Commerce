from typing import Protocol
from uuid import UUID

from src.domain.entities.admin_user import AdminUser


class AdminUserRepository(Protocol):
    async def get_by_id(self, tenant_id: UUID, user_id: UUID) -> AdminUser | None: ...

    async def get_by_email(self, tenant_id: UUID, email: str) -> AdminUser | None: ...

    async def add(self, admin_user: AdminUser) -> AdminUser: ...

    async def update(self, admin_user: AdminUser) -> AdminUser: ...
