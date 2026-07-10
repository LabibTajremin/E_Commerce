from dataclasses import dataclass
from uuid import UUID

from src.application.dto.auth import TokenPair
from src.core.security import create_token, verify_password
from src.domain.exceptions import AuthenticationError
from src.domain.repositories.admin_user_repository import AdminUserRepository


@dataclass(frozen=True, slots=True)
class LoginInput:
    tenant_id: UUID
    email: str
    password: str


class LoginUseCase:
    def __init__(self, admin_user_repository: AdminUserRepository) -> None:
        self._admin_users = admin_user_repository

    async def execute(self, data: LoginInput) -> TokenPair:
        user = await self._admin_users.get_by_email(data.tenant_id, data.email)
        if user is None or not user.is_active:
            raise AuthenticationError("Invalid credentials")
        if not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")

        access_token, _ = create_token(
            subject=user.id, tenant_id=user.tenant_id, token_type="access", role=user.role.value
        )
        refresh_token, _ = create_token(
            subject=user.id, tenant_id=user.tenant_id, token_type="refresh", role=user.role.value
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)
