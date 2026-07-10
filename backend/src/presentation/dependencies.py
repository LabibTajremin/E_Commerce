from collections.abc import AsyncIterator
from typing import Annotated, Any
from uuid import UUID

from fastapi import Depends, Header, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.dto.auth import (
    AuthenticatedAdmin,
    AuthenticatedCustomer,
    AuthenticatedPlatformAdmin,
)
from src.application.interfaces.cache import Cache
from src.application.interfaces.payment_gateway import PaymentGateway
from src.application.interfaces.storage import ObjectStorage
from src.application.interfaces.token_blacklist import TokenBlacklist
from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.use_cases.auth.login_platform_admin import PLATFORM_SUPERADMIN_ROLE
from src.application.use_cases.billing.get_effective_plan import GetEffectivePlanUseCase
from src.application.use_cases.cart.get_or_create_cart import CartIdentity
from src.application.use_cases.themes.get_store_settings import GetStoreSettingsUseCase
from src.core.security import decode_token
from src.domain.entities.admin_user import AdminRole
from src.domain.exceptions import AuthenticationError, PermissionDeniedError, ValidationError
from src.domain.repositories.admin_user_repository import AdminUserRepository
from src.domain.repositories.cart_repository import CartRepository
from src.domain.repositories.category_repository import CategoryRepository
from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.repositories.order_repository import OrderRepository
from src.domain.repositories.platform_admin_repository import PlatformAdminRepository
from src.domain.repositories.product_repository import ProductRepository
from src.domain.repositories.store_settings_repository import StoreSettingsRepository
from src.domain.repositories.subscription_plan_repository import SubscriptionPlanRepository
from src.domain.repositories.tenant_repository import TenantRepository
from src.domain.repositories.tenant_subscription_repository import TenantSubscriptionRepository
from src.domain.repositories.theme_repository import ThemeRepository
from src.infrastructure.cache.redis_cache import RedisCache
from src.infrastructure.cache.redis_client import get_redis
from src.infrastructure.cache.redis_token_blacklist import RedisTokenBlacklist
from src.infrastructure.db.repositories.sqlalchemy_admin_user_repository import (
    SqlAlchemyAdminUserRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_cart_repository import SqlAlchemyCartRepository
from src.infrastructure.db.repositories.sqlalchemy_category_repository import (
    SqlAlchemyCategoryRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_order_repository import (
    SqlAlchemyOrderRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_platform_admin_repository import (
    SqlAlchemyPlatformAdminRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_store_settings_repository import (
    SqlAlchemyStoreSettingsRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_subscription_plan_repository import (
    SqlAlchemySubscriptionPlanRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_subscription_repository import (
    SqlAlchemyTenantSubscriptionRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_theme_repository import (
    SqlAlchemyThemeRepository,
)
from src.infrastructure.db.session import async_session_factory
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork
from src.infrastructure.payments.stripe_gateway import StripePaymentGateway
from src.infrastructure.storage.s3_storage import S3ObjectStorage

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


def get_theme_repository(session: DbSession) -> ThemeRepository:
    return SqlAlchemyThemeRepository(session)


ThemeRepositoryDep = Annotated[ThemeRepository, Depends(get_theme_repository)]


def get_store_settings_repository(session: DbSession) -> StoreSettingsRepository:
    return SqlAlchemyStoreSettingsRepository(session)


StoreSettingsRepositoryDep = Annotated[
    StoreSettingsRepository, Depends(get_store_settings_repository)
]


def get_object_storage() -> ObjectStorage:
    return S3ObjectStorage()


ObjectStorageDep = Annotated[ObjectStorage, Depends(get_object_storage)]


def get_get_store_settings_use_case(
    store_settings_repository: StoreSettingsRepositoryDep, theme_repository: ThemeRepositoryDep
) -> GetStoreSettingsUseCase:
    return GetStoreSettingsUseCase(store_settings_repository, theme_repository)


GetStoreSettingsUseCaseDep = Annotated[
    GetStoreSettingsUseCase, Depends(get_get_store_settings_use_case)
]


def get_category_repository(session: DbSession) -> CategoryRepository:
    return SqlAlchemyCategoryRepository(session)


CategoryRepositoryDep = Annotated[CategoryRepository, Depends(get_category_repository)]


def get_product_repository(session: DbSession) -> ProductRepository:
    return SqlAlchemyProductRepository(session)


ProductRepositoryDep = Annotated[ProductRepository, Depends(get_product_repository)]


def get_cache() -> Cache:
    return RedisCache(get_redis())


CacheDep = Annotated[Cache, Depends(get_cache)]


def get_platform_admin_repository(session: DbSession) -> PlatformAdminRepository:
    return SqlAlchemyPlatformAdminRepository(session)


PlatformAdminRepositoryDep = Annotated[
    PlatformAdminRepository, Depends(get_platform_admin_repository)
]


async def require_platform_admin(
    token_blacklist: TokenBlacklistDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
) -> AuthenticatedPlatformAdmin:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    if payload.get("type") != "access":
        raise AuthenticationError("Not an access token")
    if payload.get("role") != PLATFORM_SUPERADMIN_ROLE:
        raise PermissionDeniedError("Not a platform admin")
    if await token_blacklist.is_revoked(payload["jti"]):
        raise AuthenticationError("Token has been revoked")

    return AuthenticatedPlatformAdmin(admin_id=UUID(payload["sub"]))


CurrentPlatformAdminDep = Annotated[AuthenticatedPlatformAdmin, Depends(require_platform_admin)]


def get_customer_repository(session: DbSession) -> CustomerRepository:
    return SqlAlchemyCustomerRepository(session)


CustomerRepositoryDep = Annotated[CustomerRepository, Depends(get_customer_repository)]


def get_cart_repository(session: DbSession) -> CartRepository:
    return SqlAlchemyCartRepository(session)


CartRepositoryDep = Annotated[CartRepository, Depends(get_cart_repository)]


def get_order_repository(session: DbSession) -> OrderRepository:
    return SqlAlchemyOrderRepository(session)


OrderRepositoryDep = Annotated[OrderRepository, Depends(get_order_repository)]


async def get_current_customer(
    resolved_tenant_id: ResolvedTenantIdDep,
    token_blacklist: TokenBlacklistDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
) -> AuthenticatedCustomer:
    if credentials is None:
        raise AuthenticationError("Missing bearer token")
    try:
        payload = decode_token(credentials.credentials)
    except ValueError as exc:
        raise AuthenticationError("Invalid or expired token") from exc

    if payload.get("type") != "access" or payload.get("role") != "customer":
        raise AuthenticationError("Not a customer access token")
    if await token_blacklist.is_revoked(payload["jti"]):
        raise AuthenticationError("Token has been revoked")

    token_tenant_id = UUID(payload["tenant_id"])
    if resolved_tenant_id is not None and resolved_tenant_id != token_tenant_id:
        raise PermissionDeniedError("Token does not match resolved tenant")

    return AuthenticatedCustomer(customer_id=UUID(payload["sub"]), tenant_id=token_tenant_id)


CurrentCustomerDep = Annotated[AuthenticatedCustomer, Depends(get_current_customer)]


async def get_cart_identity(
    resolved_tenant_id: ResolvedTenantIdDep,
    token_blacklist: TokenBlacklistDep,
    x_cart_session_id: Annotated[str | None, Header()] = None,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)] = None,
) -> CartIdentity:
    """Resolves the cart owner: an authenticated customer's bearer token takes
    priority; otherwise falls back to the anonymous X-Cart-Session-Id header
    (Section 6's "Cart (session or authenticated customer)")."""
    if resolved_tenant_id is None:
        raise AuthenticationError("Store not resolved")

    if credentials is not None:
        try:
            payload = decode_token(credentials.credentials)
        except ValueError:
            payload = None
        if (
            payload is not None
            and payload.get("type") == "access"
            and payload.get("role") == "customer"
            and not await token_blacklist.is_revoked(payload["jti"])
        ):
            return CartIdentity(tenant_id=resolved_tenant_id, customer_id=UUID(payload["sub"]))

    if x_cart_session_id:
        return CartIdentity(tenant_id=resolved_tenant_id, session_id=x_cart_session_id)

    raise ValidationError("Provide a customer bearer token or an X-Cart-Session-Id header")


CartIdentityDep = Annotated[CartIdentity, Depends(get_cart_identity)]


def get_subscription_plan_repository(session: DbSession) -> SubscriptionPlanRepository:
    return SqlAlchemySubscriptionPlanRepository(session)


SubscriptionPlanRepositoryDep = Annotated[
    SubscriptionPlanRepository, Depends(get_subscription_plan_repository)
]


def get_tenant_subscription_repository(session: DbSession) -> TenantSubscriptionRepository:
    return SqlAlchemyTenantSubscriptionRepository(session)


TenantSubscriptionRepositoryDep = Annotated[
    TenantSubscriptionRepository, Depends(get_tenant_subscription_repository)
]


def get_get_effective_plan_use_case(
    plan_repository: SubscriptionPlanRepositoryDep,
    subscription_repository: TenantSubscriptionRepositoryDep,
) -> GetEffectivePlanUseCase:
    return GetEffectivePlanUseCase(plan_repository, subscription_repository)


GetEffectivePlanUseCaseDep = Annotated[
    GetEffectivePlanUseCase, Depends(get_get_effective_plan_use_case)
]


def get_payment_gateway() -> PaymentGateway:
    return StripePaymentGateway()


PaymentGatewayDep = Annotated[PaymentGateway, Depends(get_payment_gateway)]
