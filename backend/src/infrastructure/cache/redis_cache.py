from redis.asyncio import Redis

_VERSION_PREFIX = "cache_version:"


class RedisCache:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def get(self, key: str) -> str | None:
        value = await self._redis.get(key)
        return str(value) if value is not None else None

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        await self._redis.setex(key, ttl_seconds, value)

    async def get_version(self, namespace: str) -> int:
        value = await self._redis.get(f"{_VERSION_PREFIX}{namespace}")
        return int(value) if value is not None else 0

    async def bump_version(self, namespace: str) -> None:
        await self._redis.incr(f"{_VERSION_PREFIX}{namespace}")
