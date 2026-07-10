from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.core.config import settings
from src.core.logging import configure_logging, get_logger
from src.domain.exceptions import (
    AuthenticationError,
    DomainError,
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PermissionDeniedError,
    PlanLimitExceededError,
    ValidationError,
)
from src.presentation.api.v1.admin.auth import router as admin_auth_router
from src.presentation.api.v1.admin.branding import router as admin_branding_router
from src.presentation.api.v1.admin.me import router as admin_me_router
from src.presentation.api.v1.auth.register import router as auth_register_router
from src.presentation.api.v1.platform.tenants import router as platform_tenants_router
from src.presentation.api.v1.storefront.context import router as storefront_context_router
from src.presentation.middleware.tenant_resolver import TenantResolverMiddleware

configure_logging(debug=settings.debug)
logger = get_logger(__name__)

app = FastAPI(title=settings.app_name, debug=settings.debug)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TenantResolverMiddleware, base_domain=settings.platform_base_domain)

_ERROR_STATUS_MAP: dict[type[DomainError], int] = {
    EntityNotFoundError: status.HTTP_404_NOT_FOUND,
    EntityAlreadyExistsError: status.HTTP_409_CONFLICT,
    ValidationError: status.HTTP_422_UNPROCESSABLE_ENTITY,
    AuthenticationError: status.HTTP_401_UNAUTHORIZED,
    PermissionDeniedError: status.HTTP_403_FORBIDDEN,
    PlanLimitExceededError: status.HTTP_402_PAYMENT_REQUIRED,
}


@app.exception_handler(DomainError)
async def domain_error_handler(request: Request, exc: DomainError) -> JSONResponse:
    status_code = _ERROR_STATUS_MAP.get(type(exc), status.HTTP_400_BAD_REQUEST)
    logger.warning("domain_error", error=str(exc), path=request.url.path)
    return JSONResponse(status_code=status_code, content={"detail": str(exc)})


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
    # Value objects (ColorHex, Subdomain, Email, ...) raise plain ValueError on
    # invalid input; treat that the same as a domain ValidationError (422).
    logger.warning("value_error", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, content={"detail": str(exc)}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("unhandled_exception", error=str(exc), path=request.url.path)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"},
    )


@app.get("/health", tags=["health"])
async def health_check() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(platform_tenants_router, prefix="/api/v1/platform")
app.include_router(storefront_context_router, prefix="/api/v1/storefront")
app.include_router(auth_register_router, prefix="/api/v1/auth")
app.include_router(admin_auth_router, prefix="/api/v1/admin")
app.include_router(admin_me_router, prefix="/api/v1/admin")
app.include_router(admin_branding_router, prefix="/api/v1/admin")
