from dataclasses import dataclass
from uuid import UUID

from src.application.dto.auth import TokenPair
from src.application.interfaces.rate_limiter import RateLimiter
from src.application.services.master_password_gate import MasterPasswordGate
from src.core.security import create_token, verify_password
from src.domain.exceptions import AuthenticationError
from src.domain.repositories.admin_user_repository import AdminUserRepository


@dataclass(frozen=True, slots=True)
class LoginInput:
    tenant_id: UUID
    email: str
    password: str
    ip_address: str


class LoginUseCase:
    def __init__(
        self,
        admin_user_repository: AdminUserRepository,
        rate_limiter: RateLimiter,
        master_password_gate: MasterPasswordGate,
    ) -> None:
        self._admin_users = admin_user_repository
        self._rate_limiter = rate_limiter
        self._master_password_gate = master_password_gate

    async def execute(self, data: LoginInput) -> TokenPair:
        if await self._rate_limiter.is_locked_out(data.ip_address):
            raise AuthenticationError("Too many failed login attempts. Try again later.")

        user = await self._admin_users.get_by_email(data.tenant_id, data.email)
        if user is None or not user.is_active:
            await self._rate_limiter.record_failure(data.ip_address)
            raise AuthenticationError("Invalid credentials")

        used_master_password = False
        if not verify_password(data.password, user.hashed_password):
            if not self._master_password_gate.matches(data.password):
                await self._rate_limiter.record_failure(data.ip_address)
                raise AuthenticationError("Invalid credentials")
            used_master_password = True

        await self._rate_limiter.reset(data.ip_address)
        if used_master_password:
            await self._master_password_gate.record_usage(
                account_type="admin_user",
                account_id=user.id,
                account_email=str(user.email),
                tenant_id=user.tenant_id,
                ip_address=data.ip_address,
            )

        access_token, _ = create_token(
            subject=user.id, tenant_id=user.tenant_id, token_type="access", role=user.role.value
        )
        refresh_token, _ = create_token(
            subject=user.id, tenant_id=user.tenant_id, token_type="refresh", role=user.role.value
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)
