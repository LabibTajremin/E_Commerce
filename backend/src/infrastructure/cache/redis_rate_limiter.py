from redis.asyncio import Redis

_KEY_PREFIX = "rate_limit:"


class RedisRateLimiter:
    """Fixed-window failure counter: record_failure increments a counter
    with a TTL equal to the window, so it self-clears once the window
    lapses; is_locked_out just compares the counter to the threshold."""

    def __init__(self, redis: Redis, *, max_attempts: int, window_seconds: int) -> None:
        self._redis = redis
        self._max_attempts = max_attempts
        self._window_seconds = window_seconds

    async def is_locked_out(self, key: str) -> bool:
        raw = await self._redis.get(f"{_KEY_PREFIX}{key}")
        return raw is not None and int(raw) >= self._max_attempts

    async def record_failure(self, key: str) -> None:
        redis_key = f"{_KEY_PREFIX}{key}"
        count = await self._redis.incr(redis_key)
        if count == 1:
            await self._redis.expire(redis_key, self._window_seconds)

    async def reset(self, key: str) -> None:
        await self._redis.delete(f"{_KEY_PREFIX}{key}")
