from fastapi import APIRouter, HTTPException, status

from src.application.use_cases.auth.login import LoginInput, LoginUseCase
from src.application.use_cases.auth.logout import LogoutInput, LogoutUseCase
from src.application.use_cases.auth.refresh_token import RefreshTokenInput, RefreshTokenUseCase
from src.presentation.dependencies import (
    AdminUserRepositoryDep,
    BearerTokenDep,
    ClientIpDep,
    CurrentAdminDep,
    MasterPasswordGateDep,
    RateLimiterDep,
    ResolvedTenantIdDep,
    TokenBlacklistDep,
)
from src.presentation.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenPairResponse,
)

router = APIRouter(prefix="/auth", tags=["admin:auth"])


@router.post("/login", response_model=TokenPairResponse)
async def login(
    body: LoginRequest,
    tenant_id: ResolvedTenantIdDep,
    admin_user_repository: AdminUserRepositoryDep,
    rate_limiter: RateLimiterDep,
    master_password_gate: MasterPasswordGateDep,
    client_ip: ClientIpDep,
) -> TokenPairResponse:
    if tenant_id is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Store not found")
    use_case = LoginUseCase(admin_user_repository, rate_limiter, master_password_gate)
    tokens = await use_case.execute(
        LoginInput(
            tenant_id=tenant_id, email=body.email, password=body.password, ip_address=client_ip
        )
    )
    return TokenPairResponse(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    body: RefreshTokenRequest,
    admin_user_repository: AdminUserRepositoryDep,
    token_blacklist: TokenBlacklistDep,
) -> TokenPairResponse:
    use_case = RefreshTokenUseCase(admin_user_repository, token_blacklist)
    tokens = await use_case.execute(RefreshTokenInput(refresh_token=body.refresh_token))
    return TokenPairResponse(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    current: CurrentAdminDep,
    bearer_token: BearerTokenDep,
    token_blacklist: TokenBlacklistDep,
) -> None:
    del current  # enforces that logout requires a currently-valid access token
    use_case = LogoutUseCase(token_blacklist)
    await use_case.execute(
        LogoutInput(access_token=bearer_token or "", refresh_token=body.refresh_token)
    )
