from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from src.application.dto.auth import TokenPair
from src.application.interfaces.token_blacklist import TokenBlacklist
from src.core.security import create_token, decode_token
from src.domain.exceptions import AuthenticationError
from src.domain.repositories.admin_user_repository import AdminUserRepository


@dataclass(frozen=True, slots=True)
class RefreshTokenInput:
    refresh_token: str


class RefreshTokenUseCase:
    def __init__(
        self, admin_user_repository: AdminUserRepository, token_blacklist: TokenBlacklist
    ) -> None:
        self._admin_users = admin_user_repository
        self._blacklist = token_blacklist

    async def execute(self, data: RefreshTokenInput) -> TokenPair:
        try:
            payload = decode_token(data.refresh_token)
        except ValueError as exc:
            raise AuthenticationError("Invalid or expired refresh token") from exc

        if payload.get("type") != "refresh":
            raise AuthenticationError("Not a refresh token")

        jti = payload["jti"]
        if await self._blacklist.is_revoked(jti):
            raise AuthenticationError("Refresh token has been revoked")

        tenant_id = UUID(payload["tenant_id"])
        user_id = UUID(payload["sub"])
        user = await self._admin_users.get_by_id(tenant_id, user_id)
        if user is None or not user.is_active:
            raise AuthenticationError("User no longer active")

        remaining_ttl = max(1, int(payload["exp"] - datetime.now(UTC).timestamp()))
        await self._blacklist.revoke(jti, remaining_ttl)

        access_token, _ = create_token(
            subject=user.id, tenant_id=user.tenant_id, token_type="access", role=user.role.value
        )
        new_refresh_token, _ = create_token(
            subject=user.id, tenant_id=user.tenant_id, token_type="refresh", role=user.role.value
        )
        return TokenPair(access_token=access_token, refresh_token=new_refresh_token)
