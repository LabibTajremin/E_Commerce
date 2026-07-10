from dataclasses import dataclass

from src.application.dto.auth import TokenPair
from src.core.security import create_token, verify_password
from src.domain.exceptions import AuthenticationError
from src.domain.repositories.platform_admin_repository import PlatformAdminRepository

PLATFORM_SUPERADMIN_ROLE = "platform_superadmin"


@dataclass(frozen=True, slots=True)
class LoginPlatformAdminInput:
    email: str
    password: str


class LoginPlatformAdminUseCase:
    def __init__(self, platform_admin_repository: PlatformAdminRepository) -> None:
        self._platform_admins = platform_admin_repository

    async def execute(self, data: LoginPlatformAdminInput) -> TokenPair:
        admin = await self._platform_admins.get_by_email(data.email)
        if admin is None or not verify_password(data.password, admin.hashed_password):
            raise AuthenticationError("Invalid credentials")

        access_token, _ = create_token(
            subject=admin.id, tenant_id=None, token_type="access", role=PLATFORM_SUPERADMIN_ROLE
        )
        refresh_token, _ = create_token(
            subject=admin.id, tenant_id=None, token_type="refresh", role=PLATFORM_SUPERADMIN_ROLE
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)
