from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.infrastructure.db.session import get_session

# Paths that never carry tenant context (platform/superadmin, health, docs).
_EXEMPT_PREFIXES = ("/api/v1/platform", "/health", "/docs", "/openapi.json", "/redoc")


def extract_subdomain(host: str, base_domain: str) -> str | None:
    """Extract the tenant subdomain label from a Host header.

    Supports local dev hosts like `acme.localhost:3000` (base_domain="localhost")
    as well as production hosts like `acme.yourplatform.com`.
    """
    hostname = host.split(":")[0].lower()
    if hostname == base_domain or not hostname.endswith(f".{base_domain}"):
        return None
    label = hostname[: -(len(base_domain) + 1)]
    return label or None


class TenantResolverMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, base_domain: str = "localhost") -> None:  # type: ignore[no-untyped-def]
        super().__init__(app)
        self._base_domain = base_domain

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.url.path.startswith(_EXEMPT_PREFIXES):
            return await call_next(request)

        host = request.headers.get("host", "")
        subdomain = extract_subdomain(host, self._base_domain)

        tenant = None
        async with get_session() as session:
            repo = SqlAlchemyTenantRepository(session)
            if subdomain:
                tenant = await repo.get_by_subdomain(subdomain)
            if tenant is None:
                tenant = await repo.get_by_custom_domain(host.split(":")[0].lower())

        if tenant is None or not tenant.is_active:
            return JSONResponse(status_code=404, content={"detail": "Store not found"})

        request.state.tenant_id = tenant.id
        return await call_next(request)
