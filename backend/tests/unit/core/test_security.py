from uuid import uuid4

import pytest

from src.core.security import create_token, decode_token, hash_password, verify_password


def test_hash_password_round_trips() -> None:
    hashed = hash_password("correct-horse-battery-staple")
    assert verify_password("correct-horse-battery-staple", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_hash_password_never_stores_plaintext() -> None:
    hashed = hash_password("supersecret")
    assert "supersecret" not in hashed


def test_create_and_decode_access_token() -> None:
    user_id = uuid4()
    tenant_id = uuid4()
    token, jti = create_token(
        subject=user_id, tenant_id=tenant_id, token_type="access", role="owner"
    )

    payload = decode_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["tenant_id"] == str(tenant_id)
    assert payload["type"] == "access"
    assert payload["role"] == "owner"
    assert payload["jti"] == jti


def test_decode_token_rejects_garbage() -> None:
    with pytest.raises(ValueError):
        decode_token("not-a-real-token")


def test_access_and_refresh_tokens_have_distinct_jtis() -> None:
    user_id = uuid4()
    tenant_id = uuid4()
    _, access_jti = create_token(
        subject=user_id, tenant_id=tenant_id, token_type="access", role="owner"
    )
    _, refresh_jti = create_token(
        subject=user_id, tenant_id=tenant_id, token_type="refresh", role="owner"
    )
    assert access_jti != refresh_jti
