from dataclasses import dataclass
from datetime import UTC, datetime

from src.application.interfaces.token_blacklist import TokenBlacklist
from src.core.security import decode_token


@dataclass(frozen=True, slots=True)
class LogoutInput:
    access_token: str
    refresh_token: str | None = None


class LogoutUseCase:
    def __init__(self, token_blacklist: TokenBlacklist) -> None:
        self._blacklist = token_blacklist

    async def execute(self, data: LogoutInput) -> None:
        for token in (data.access_token, data.refresh_token):
            if not token:
                continue
            try:
                payload = decode_token(token)
            except ValueError:
                continue
            ttl = max(1, int(payload["exp"] - datetime.now(UTC).timestamp()))
            await self._blacklist.revoke(payload["jti"], ttl)
