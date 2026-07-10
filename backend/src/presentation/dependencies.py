from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth import AuthenticatedAdmin
from src.application.interfaces.token_blacklist import TokenBlacklist
from src.application.interfaces.unit_of_work import UnitOfWork
from src.core.config import settings
from src.core.security import decode_token
from src.domain.entities.admin_user import AdminRole
from src.domain.exceptions import AuthenticationError, PermissionDeniedError
from src.domain.repositories.admin_user_repository import AdminUserRepository
from src.domain.repositories.tenant_repository import TenantRepository
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_token_blacklist import RedisTokenBlacklist
from src.infrastructure.db.repositories.sqlalchemy_admin_user_repository import (
    SqlAlchemyAdminUserRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.infrastructure.db.session import async_session_factory
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_db_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with async_session_factory() as session:
        tenant_id = getattr(request.state, "tenant_id", None)
        try:
            if tenant_id is not None:
                # UUID from resolved tenant context, not raw client input; see unit_of_work.py.
                await session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def get_tenant_repository(session: DbSession) -> TenantRepository:
    return SqlAlchemyTenantRepository(session)


TenantRepositoryDep = Annotated[TenantRepository, Depends(get_tenant_repository)]


def get_admin_user_repository(session: DbSession) -> AdminUserRepository:
    return SqlAlchemyAdminUserRepository(session)


AdminUserRepositoryDep = Annotated[AdminUserRepository, Depends(get_admin_user_repository)]


def get_unit_of_work(request: Request) -> UnitOfWork:
    tenant_id = getattr(request.state, "tenant_id", None)
    return SqlAlchemyUnitOfWork(tenant_id=tenant_id)


UnitOfWorkDep = Annotated[UnitOfWork, Depends(get_unit_of_work)]


def get_token_blacklist() -> TokenBlacklist:
    return RedisTokenBlacklist(get_redis())


TokenBlacklistDep = Annotated[TokenBlacklist, Depends(get_token_blacklist)]


def get_resolved_tenant_id(request: Request) -> UUID | None:
    return getattr(request.state, "tenant_id", None)


ResolvedTenantIdDep = Annotated[UUID | None, Depends(get_resolved_tenant_id)]


async def get_current_admin_user(
    resolved_tenant_id: ResolvedTenantIdDep,
    token_blacklist: TokenBlacklistDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
) -> AuthenticatedAdmin:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Not an access token")
    if await token_blacklist.is_revoked(payload["jti"]):
        raise AuthenticationError("Token has been revoked")

    token_tenant_id = UUID(payload["tenant_id"])
    # Subdomain-resolved tenant (if any) must match the JWT's tenant claim — this is
    # the explicit cross-tenant leakage guard required by Section 4/Phase 2.
    if resolved_tenant_id is not None and resolved_tenant_id != token_tenant_id:
        raise PermissionDeniedError("Token does not match resolved tenant")

    return AuthenticatedAdmin(
        user_id=UUID(payload["sub"]), tenant_id=token_tenant_id, role=payload["role"]
    )


CurrentAdminDep = Annotated[AuthenticatedAdmin, Depends(get_current_admin_user)]


async def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
) -> str | None:
    return credentials.credentials if credentials else None


BearerTokenDep = Annotated[str | None, Depends(get_bearer_token)]


def require_role(*allowed_roles: AdminRole) -> Any:
    async def _check(current: CurrentAdminDep) -> AuthenticatedAdmin:
        if current.role not in {role.value for role in allowed_roles}:
            raise PermissionDeniedError("Insufficient role")
        return current

    return Depends(_check)


async def require_platform_admin(
    x_platform_admin_key: Annotated[str | None, Header()] = None,
) -> None:
    """Interim static-secret gate; Phase 8 replaces this with real superadmin auth."""
    if x_platform_admin_key != settings.platform_admin_api_key:
        raise AuthenticationError("Invalid platform admin credentials")
