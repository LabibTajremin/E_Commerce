from redis.asyncio import Redis

_KEY_PREFIX = "revoked_token:"


class RedisTokenBlacklist:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        await self._redis.setex(f"{_KEY_PREFIX}{jti}", ttl_seconds, "1")

    async def is_revoked(self, jti: str) -> bool:
        return bool(await self._redis.exists(f"{_KEY_PREFIX}{jti}"))
