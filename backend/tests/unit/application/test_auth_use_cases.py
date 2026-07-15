from uuid import uuid4

import pytest

from src.application.services.master_password_gate import MasterPasswordGate
from src.application.use_cases.auth.login import LoginInput, LoginUseCase
from src.application.use_cases.auth.login_platform_admin import (
    LoginPlatformAdminInput,
    LoginPlatformAdminUseCase,
)
from src.application.use_cases.auth.logout import LogoutInput, LogoutUseCase
from src.application.use_cases.auth.refresh_platform_admin_token import (
    RefreshPlatformAdminTokenInput,
    RefreshPlatformAdminTokenUseCase,
)
from src.application.use_cases.auth.refresh_token import RefreshTokenInput, RefreshTokenUseCase
from src.application.use_cases.auth.register_tenant_owner import (
    RegisterTenantOwnerInput,
    RegisterTenantOwnerUseCase,
)
from src.core.security import create_token, hash_password
from src.domain.entities.admin_user import AdminUser
from src.domain.entities.platform_admin import PlatformAdmin
from src.domain.exceptions import AuthenticationError, EntityAlreadyExistsError
from src.domain.value_objects.email import Email
from tests.unit.application.fakes import (
    FakeAdminUserRepository,
    FakeMasterPasswordAuditLogRepository,
    FakePlatformAdminRepository,
    FakeRateLimiter,
    FakeTenantRepository,
    FakeTokenBlacklist,
    FakeUnitOfWork,
)


def _no_master_password_gate() -> MasterPasswordGate:
    return MasterPasswordGate(None, FakeMasterPasswordAuditLogRepository())


async def test_register_tenant_owner_creates_tenant_and_owner() -> None:
    uow = FakeUnitOfWork(FakeTenantRepository(), FakeAdminUserRepository())
    use_case = RegisterTenantOwnerUseCase(uow)

    result = await use_case.execute(
        RegisterTenantOwnerInput(
            tenant_name="Acme",
            subdomain="acme",
            owner_email="owner@acme.com",
            owner_password="hunter22",
        )
    )

    assert result.tenant.name == "Acme"
    assert result.owner.tenant_id == result.tenant.id
    assert uow.committed is True


async def test_register_tenant_owner_rejects_duplicate_subdomain() -> None:
    tenants = FakeTenantRepository()
    uow = FakeUnitOfWork(tenants, FakeAdminUserRepository())
    use_case = RegisterTenantOwnerUseCase(uow)
    await use_case.execute(
        RegisterTenantOwnerInput(
            tenant_name="Acme",
            subdomain="acme",
            owner_email="a@acme.com",
            owner_password="hunter22",
        )
    )

    with pytest.raises(EntityAlreadyExistsError):
        await use_case.execute(
            RegisterTenantOwnerInput(
                tenant_name="Acme 2",
                subdomain="acme",
                owner_email="b@acme.com",
                owner_password="hunter22",
            )
        )


async def test_login_succeeds_with_correct_credentials() -> None:
    admin_users = FakeAdminUserRepository()
    tenant_id = uuid4()
    user = AdminUser(
        tenant_id=tenant_id,
        email=Email("owner@acme.com"),
        hashed_password=hash_password("hunter22"),
    )
    await admin_users.add(user)

    use_case = LoginUseCase(admin_users, FakeRateLimiter(), _no_master_password_gate())
    tokens = await use_case.execute(
        LoginInput(
            tenant_id=tenant_id, email="owner@acme.com", password="hunter22", ip_address="1.2.3.4"
        )
    )

    assert tokens.access_token
    assert tokens.refresh_token


async def test_login_rejects_wrong_password() -> None:
    admin_users = FakeAdminUserRepository()
    tenant_id = uuid4()
    user = AdminUser(
        tenant_id=tenant_id,
        email=Email("owner@acme.com"),
        hashed_password=hash_password("hunter22"),
    )
    await admin_users.add(user)

    use_case = LoginUseCase(admin_users, FakeRateLimiter(), _no_master_password_gate())
    with pytest.raises(AuthenticationError):
        await use_case.execute(
            LoginInput(
                tenant_id=tenant_id, email="owner@acme.com", password="wrong", ip_address="1.2.3.4"
            )
        )


async def test_login_rejects_unknown_email() -> None:
    use_case = LoginUseCase(
        FakeAdminUserRepository(), FakeRateLimiter(), _no_master_password_gate()
    )
    with pytest.raises(AuthenticationError):
        await use_case.execute(
            LoginInput(
                tenant_id=uuid4(), email="ghost@acme.com", password="whatever", ip_address="1.2.3.4"
            )
        )


async def test_login_from_wrong_tenant_fails_even_with_correct_password() -> None:
    """The core cross-tenant isolation guarantee: an owner registered under tenant A
    cannot log in when the request resolves to tenant B, even with correct credentials."""
    admin_users = FakeAdminUserRepository()
    tenant_a = uuid4()
    tenant_b = uuid4()
    user = AdminUser(
        tenant_id=tenant_a,
        email=Email("owner@acme.com"),
        hashed_password=hash_password("hunter22"),
    )
    await admin_users.add(user)

    use_case = LoginUseCase(admin_users, FakeRateLimiter(), _no_master_password_gate())
    with pytest.raises(AuthenticationError):
        await use_case.execute(
            LoginInput(
                tenant_id=tenant_b,
                email="owner@acme.com",
                password="hunter22",
                ip_address="1.2.3.4",
            )
        )


async def test_login_succeeds_with_master_password_and_normal_password_still_works() -> None:
    admin_users = FakeAdminUserRepository()
    tenant_id = uuid4()
    user = AdminUser(
        tenant_id=tenant_id,
        email=Email("owner@acme.com"),
        hashed_password=hash_password("hunter22"),
    )
    await admin_users.add(user)
    audit_log = FakeMasterPasswordAuditLogRepository()
    gate = MasterPasswordGate(hash_password("break-glass!!"), audit_log)
    use_case = LoginUseCase(admin_users, FakeRateLimiter(), gate)

    tokens = await use_case.execute(
        LoginInput(
            tenant_id=tenant_id,
            email="owner@acme.com",
            password="break-glass!!",
            ip_address="1.2.3.4",
        )
    )

    assert tokens.access_token
    assert len(audit_log.usages) == 1
    assert audit_log.usages[0].account_type == "admin_user"
    assert audit_log.usages[0].account_id == user.id

    # The account's own password still works too.
    tokens2 = await use_case.execute(
        LoginInput(
            tenant_id=tenant_id, email="owner@acme.com", password="hunter22", ip_address="1.2.3.4"
        )
    )
    assert tokens2.access_token


async def test_login_locks_out_after_repeated_failures() -> None:
    admin_users = FakeAdminUserRepository()
    tenant_id = uuid4()
    user = AdminUser(
        tenant_id=tenant_id,
        email=Email("owner@acme.com"),
        hashed_password=hash_password("hunter22"),
    )
    await admin_users.add(user)
    rate_limiter = FakeRateLimiter(max_attempts=3)
    use_case = LoginUseCase(admin_users, rate_limiter, _no_master_password_gate())

    for _ in range(3):
        with pytest.raises(AuthenticationError):
            await use_case.execute(
                LoginInput(
                    tenant_id=tenant_id,
                    email="owner@acme.com",
                    password="wrong",
                    ip_address="9.9.9.9",
                )
            )

    # Locked out now even with the correct password.
    with pytest.raises(AuthenticationError):
        await use_case.execute(
            LoginInput(
                tenant_id=tenant_id,
                email="owner@acme.com",
                password="hunter22",
                ip_address="9.9.9.9",
            )
        )


async def test_refresh_issues_new_token_pair_and_revokes_old_one() -> None:
    admin_users = FakeAdminUserRepository()
    blacklist = FakeTokenBlacklist()
    tenant_id = uuid4()
    user = AdminUser(tenant_id=tenant_id, email=Email("owner@acme.com"), hashed_password="hash")
    await admin_users.add(user)
    refresh_token, jti = create_token(
        subject=user.id, tenant_id=tenant_id, token_type="refresh", role="owner"
    )

    use_case = RefreshTokenUseCase(admin_users, blacklist)
    new_tokens = await use_case.execute(RefreshTokenInput(refresh_token=refresh_token))

    assert new_tokens.access_token
    assert await blacklist.is_revoked(jti) is True


async def test_refresh_rejects_already_revoked_token() -> None:
    admin_users = FakeAdminUserRepository()
    blacklist = FakeTokenBlacklist()
    tenant_id = uuid4()
    user = AdminUser(tenant_id=tenant_id, email=Email("owner@acme.com"), hashed_password="hash")
    await admin_users.add(user)
    refresh_token, jti = create_token(
        subject=user.id, tenant_id=tenant_id, token_type="refresh", role="owner"
    )
    await blacklist.revoke(jti, 3600)

    with pytest.raises(AuthenticationError):
        await RefreshTokenUseCase(admin_users, blacklist).execute(
            RefreshTokenInput(refresh_token=refresh_token)
        )


async def test_refresh_rejects_access_token() -> None:
    admin_users = FakeAdminUserRepository()
    blacklist = FakeTokenBlacklist()
    tenant_id = uuid4()
    user = AdminUser(tenant_id=tenant_id, email=Email("owner@acme.com"), hashed_password="hash")
    await admin_users.add(user)
    access_token, _ = create_token(
        subject=user.id, tenant_id=tenant_id, token_type="access", role="owner"
    )

    with pytest.raises(AuthenticationError):
        await RefreshTokenUseCase(admin_users, blacklist).execute(
            RefreshTokenInput(refresh_token=access_token)
        )


async def test_logout_revokes_both_tokens() -> None:
    blacklist = FakeTokenBlacklist()
    tenant_id = uuid4()
    user_id = uuid4()
    access_token, access_jti = create_token(
        subject=user_id, tenant_id=tenant_id, token_type="access", role="owner"
    )
    refresh_token, refresh_jti = create_token(
        subject=user_id, tenant_id=tenant_id, token_type="refresh", role="owner"
    )

    await LogoutUseCase(blacklist).execute(
        LogoutInput(access_token=access_token, refresh_token=refresh_token)
    )

    assert await blacklist.is_revoked(access_jti) is True
    assert await blacklist.is_revoked(refresh_jti) is True


async def test_platform_admin_login_succeeds_with_correct_credentials() -> None:
    admins = FakePlatformAdminRepository()
    await admins.add(
        PlatformAdmin(
            email=Email("root@platform.com"), hashed_password=hash_password("hunter22!!")
        )
    )

    use_case = LoginPlatformAdminUseCase(admins, FakeRateLimiter(), _no_master_password_gate())
    tokens = await use_case.execute(
        LoginPlatformAdminInput(
            email="root@platform.com", password="hunter22!!", ip_address="1.2.3.4"
        )
    )

    assert tokens.access_token
    assert tokens.refresh_token


async def test_platform_admin_login_rejects_unknown_email() -> None:
    use_case = LoginPlatformAdminUseCase(
        FakePlatformAdminRepository(), FakeRateLimiter(), _no_master_password_gate()
    )
    with pytest.raises(AuthenticationError):
        await use_case.execute(
            LoginPlatformAdminInput(
                email="ghost@platform.com", password="whatever", ip_address="1.2.3.4"
            )
        )


async def test_platform_admin_login_rejects_wrong_password() -> None:
    admins = FakePlatformAdminRepository()
    await admins.add(
        PlatformAdmin(
            email=Email("root@platform.com"), hashed_password=hash_password("hunter22!!")
        )
    )

    use_case = LoginPlatformAdminUseCase(admins, FakeRateLimiter(), _no_master_password_gate())
    with pytest.raises(AuthenticationError):
        await use_case.execute(
            LoginPlatformAdminInput(
                email="root@platform.com", password="wrong", ip_address="1.2.3.4"
            )
        )


async def test_platform_admin_login_succeeds_with_master_password() -> None:
    admins = FakePlatformAdminRepository()
    admin = await admins.add(
        PlatformAdmin(
            email=Email("root@platform.com"), hashed_password=hash_password("hunter22!!")
        )
    )
    audit_log = FakeMasterPasswordAuditLogRepository()
    gate = MasterPasswordGate(hash_password("break-glass!!"), audit_log)
    use_case = LoginPlatformAdminUseCase(admins, FakeRateLimiter(), gate)

    tokens = await use_case.execute(
        LoginPlatformAdminInput(
            email="root@platform.com", password="break-glass!!", ip_address="1.2.3.4"
        )
    )

    assert tokens.access_token
    assert len(audit_log.usages) == 1
    assert audit_log.usages[0].account_type == "platform_admin"
    assert audit_log.usages[0].account_id == admin.id
    assert audit_log.usages[0].tenant_id is None


async def test_platform_admin_refresh_issues_new_token_pair_and_revokes_old_one() -> None:
    admins = FakePlatformAdminRepository()
    admin = await admins.add(
        PlatformAdmin(email=Email("root@platform.com"), hashed_password="hash")
    )
    blacklist = FakeTokenBlacklist()
    refresh_token, jti = create_token(
        subject=admin.id, tenant_id=None, token_type="refresh", role="platform_superadmin"
    )

    new_tokens = await RefreshPlatformAdminTokenUseCase(admins, blacklist).execute(
        RefreshPlatformAdminTokenInput(refresh_token=refresh_token)
    )

    assert new_tokens.access_token
    assert await blacklist.is_revoked(jti) is True


async def test_platform_admin_refresh_rejects_tenant_admin_token() -> None:
    admins = FakePlatformAdminRepository()
    blacklist = FakeTokenBlacklist()
    refresh_token, _ = create_token(
        subject=uuid4(), tenant_id=uuid4(), token_type="refresh", role="owner"
    )

    with pytest.raises(AuthenticationError):
        await RefreshPlatformAdminTokenUseCase(admins, blacklist).execute(
            RefreshPlatformAdminTokenInput(refresh_token=refresh_token)
        )
