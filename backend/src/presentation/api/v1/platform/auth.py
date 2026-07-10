from fastapi import APIRouter, status

from src.application.use_cases.auth.login_platform_admin import (
    LoginPlatformAdminInput,
    LoginPlatformAdminUseCase,
)
from src.application.use_cases.auth.logout import LogoutInput, LogoutUseCase
from src.application.use_cases.auth.refresh_platform_admin_token import (
    RefreshPlatformAdminTokenInput,
    RefreshPlatformAdminTokenUseCase,
)
from src.presentation.dependencies import (
    BearerTokenDep,
    CurrentPlatformAdminDep,
    PlatformAdminRepositoryDep,
    TokenBlacklistDep,
)
from src.presentation.schemas.auth import (
    LoginRequest,
    LogoutRequest,
    RefreshTokenRequest,
    TokenPairResponse,
)

router = APIRouter(prefix="/auth", tags=["platform:auth"])


@router.post("/login", response_model=TokenPairResponse)
async def login(
    body: LoginRequest, platform_admin_repository: PlatformAdminRepositoryDep
) -> TokenPairResponse:
    use_case = LoginPlatformAdminUseCase(platform_admin_repository)
    tokens = await use_case.execute(
        LoginPlatformAdminInput(email=body.email, password=body.password)
    )
    return TokenPairResponse(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )


@router.post("/refresh", response_model=TokenPairResponse)
async def refresh(
    body: RefreshTokenRequest,
    platform_admin_repository: PlatformAdminRepositoryDep,
    token_blacklist: TokenBlacklistDep,
) -> TokenPairResponse:
    use_case = RefreshPlatformAdminTokenUseCase(platform_admin_repository, token_blacklist)
    tokens = await use_case.execute(
        RefreshPlatformAdminTokenInput(refresh_token=body.refresh_token)
    )
    return TokenPairResponse(
        access_token=tokens.access_token, refresh_token=tokens.refresh_token
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    body: LogoutRequest,
    current: CurrentPlatformAdminDep,
    bearer_token: BearerTokenDep,
    token_blacklist: TokenBlacklistDep,
) -> None:
    del current  # enforces that logout requires a currently-valid access token
    use_case = LogoutUseCase(token_blacklist)
    await use_case.execute(
        LogoutInput(access_token=bearer_token or "", refresh_token=body.refresh_token)
    )
