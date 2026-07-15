from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.application.dto.auth import TokenPair
from src.application.interfaces.token_blacklist import TokenBlacklist
from src.application.use_cases.auth.login_platform_admin import PLATFORM_SUPERADMIN_ROLE
from src.core.security import create_token, decode_token
from src.domain.exceptions import AuthenticationError
from src.domain.repositories.platform_admin_repository import PlatformAdminRepository


@dataclass(frozen=True, slots=True)
class RefreshPlatformAdminTokenInput:
    refresh_token: str


class RefreshPlatformAdminTokenUseCase:
    def __init__(
        self, platform_admin_repository: PlatformAdminRepository, token_blacklist: TokenBlacklist
    ) -> None:
        self._platform_admins = platform_admin_repository
        self._blacklist = token_blacklist

    async def execute(self, data: RefreshPlatformAdminTokenInput) -> TokenPair:
        try:
            payload = decode_token(data.refresh_token)
        except ValueError as exc:
            raise AuthenticationError("Invalid or expired refresh token") from exc

        if payload.get("type") != "refresh":
            raise AuthenticationError("Not a refresh token")
        if payload.get("role") != PLATFORM_SUPERADMIN_ROLE:
            raise AuthenticationError("Not a platform admin token")

        jti = payload["jti"]
        if await self._blacklist.is_revoked(jti):
            raise AuthenticationError("Refresh token has been revoked")

        admin_id = UUID(payload["sub"])
        admin = await self._platform_admins.get_by_id(admin_id)
        if admin is None:
            raise AuthenticationError("Platform admin no longer exists")

        remaining_ttl = max(1, int(payload["exp"] - datetime.now(UTC).timestamp()))
        await self._blacklist.revoke(jti, remaining_ttl)

        access_token, _ = create_token(
            subject=admin.id, tenant_id=None, token_type="access", role=PLATFORM_SUPERADMIN_ROLE
        )
        new_refresh_token, _ = create_token(
            subject=admin.id, tenant_id=None, token_type="refresh", role=PLATFORM_SUPERADMIN_ROLE
        )
        return TokenPair(access_token=access_token, refresh_token=new_refresh_token)
