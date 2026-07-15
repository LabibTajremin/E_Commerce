from dataclasses import dataclass

from src.application.dto.auth import TokenPair
from src.application.interfaces.rate_limiter import RateLimiter
from src.application.services.master_password_gate import MasterPasswordGate
from src.core.security import create_token, verify_password
from src.domain.exceptions import AuthenticationError
from src.domain.repositories.platform_admin_repository import PlatformAdminRepository

PLATFORM_SUPERADMIN_ROLE = "platform_superadmin"


@dataclass(frozen=True, slots=True)
class LoginPlatformAdminInput:
    email: str
    password: str
    ip_address: str


class LoginPlatformAdminUseCase:
    def __init__(
        self,
        platform_admin_repository: PlatformAdminRepository,
        rate_limiter: RateLimiter,
        master_password_gate: MasterPasswordGate,
    ) -> None:
        self._platform_admins = platform_admin_repository
        self._rate_limiter = rate_limiter
        self._master_password_gate = master_password_gate

    async def execute(self, data: LoginPlatformAdminInput) -> TokenPair:
        if await self._rate_limiter.is_locked_out(data.ip_address):
            raise AuthenticationError("Too many failed login attempts. Try again later.")

        admin = await self._platform_admins.get_by_email(data.email)
        if admin is None:
            await self._rate_limiter.record_failure(data.ip_address)
            raise AuthenticationError("Invalid credentials")

        used_master_password = False
        if not verify_password(data.password, admin.hashed_password):
            if not self._master_password_gate.matches(data.password):
                await self._rate_limiter.record_failure(data.ip_address)
                raise AuthenticationError("Invalid credentials")
            used_master_password = True

        await self._rate_limiter.reset(data.ip_address)
        if used_master_password:
            await self._master_password_gate.record_usage(
                account_type="platform_admin",
                account_id=admin.id,
                account_email=str(admin.email),
                tenant_id=None,
                ip_address=data.ip_address,
            )

        access_token, _ = create_token(
            subject=admin.id, tenant_id=None, token_type="access", role=PLATFORM_SUPERADMIN_ROLE
        )
        refresh_token, _ = create_token(
            subject=admin.id, tenant_id=None, token_type="refresh", role=PLATFORM_SUPERADMIN_ROLE
        )
        return TokenPair(access_token=access_token, refresh_token=refresh_token)
