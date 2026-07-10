from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from src.core.config import settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh"]


def hash_password(plain_password: str) -> str:
    return _pwd_context.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bool(_pwd_context.verify(plain_password, hashed_password))


def create_token(
    *,
    subject: UUID,
    tenant_id: UUID | None,
    token_type: TokenType,
    role: str,
) -> tuple[str, str]:
    """Returns (encoded_token, jti) — jti is used as the revocation key.

    tenant_id is None for platform-superadmin tokens, which aren't scoped to
    any tenant.
    """
    now = datetime.now(UTC)
    expires_delta = (
        timedelta(minutes=settings.access_token_expire_minutes)
        if token_type == "access"
        else timedelta(days=settings.refresh_token_expire_days)
    )
    jti = str(uuid4())
    payload: dict[str, Any] = {
        "sub": str(subject),
        "tenant_id": str(tenant_id) if tenant_id is not None else None,
        "type": token_type,
        "role": role,
        "jti": jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    token: str = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, jti


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc
