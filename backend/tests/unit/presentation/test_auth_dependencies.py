from uuid import uuid4

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from src.core.security import create_token
from src.domain.exceptions import AuthenticationError, PermissionDeniedError
from src.presentation.dependencies import get_current_admin_user
from tests.unit.application.fakes import FakeTokenBlacklist


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


async def test_get_current_admin_user_accepts_matching_tenant() -> None:
    tenant_id = uuid4()
    user_id = uuid4()
    token, _ = create_token(subject=user_id, tenant_id=tenant_id, token_type="access", role="owner")

    admin = await get_current_admin_user(
        resolved_tenant_id=tenant_id,
        token_blacklist=FakeTokenBlacklist(),
        credentials=_bearer(token),
    )

    assert admin.user_id == user_id
    assert admin.tenant_id == tenant_id
    assert admin.role == "owner"


async def test_get_current_admin_user_rejects_cross_tenant_token() -> None:
    """An access token minted for tenant A must be refused on a request the
    middleware resolved to tenant B — the core cross-tenant leakage guard."""
    tenant_a = uuid4()
    tenant_b = uuid4()
    token, _ = create_token(subject=uuid4(), tenant_id=tenant_a, token_type="access", role="owner")

    with pytest.raises(PermissionDeniedError):
        await get_current_admin_user(
            resolved_tenant_id=tenant_b,
            token_blacklist=FakeTokenBlacklist(),
            credentials=_bearer(token),
        )


async def test_get_current_admin_user_rejects_missing_token() -> None:
    with pytest.raises(AuthenticationError):
        await get_current_admin_user(
            resolved_tenant_id=None, token_blacklist=FakeTokenBlacklist(), credentials=None
        )


async def test_get_current_admin_user_rejects_revoked_token() -> None:
    tenant_id = uuid4()
    token, jti = create_token(
        subject=uuid4(), tenant_id=tenant_id, token_type="access", role="owner"
    )
    blacklist = FakeTokenBlacklist()
    await blacklist.revoke(jti, 3600)

    with pytest.raises(AuthenticationError):
        await get_current_admin_user(
            resolved_tenant_id=tenant_id, token_blacklist=blacklist, credentials=_bearer(token)
        )


async def test_get_current_admin_user_rejects_refresh_token_as_access() -> None:
    tenant_id = uuid4()
    token, _ = create_token(
        subject=uuid4(), tenant_id=tenant_id, token_type="refresh", role="owner"
    )

    with pytest.raises(AuthenticationError):
        await get_current_admin_user(
            resolved_tenant_id=tenant_id,
            token_blacklist=FakeTokenBlacklist(),
            credentials=_bearer(token),
        )
