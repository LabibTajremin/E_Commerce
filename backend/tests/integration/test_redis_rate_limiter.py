from redis.asyncio import Redis

from src.infrastructure.cache.redis_rate_limiter import RedisRateLimiter


async def test_locks_out_after_max_attempts(redis_url: str) -> None:
    redis = Redis.from_url(redis_url, decode_responses=True)
    limiter = RedisRateLimiter(redis, max_attempts=3, window_seconds=60)
    key = "test-lockout-key-1"

    assert await limiter.is_locked_out(key) is False

    await limiter.record_failure(key)
    await limiter.record_failure(key)
    assert await limiter.is_locked_out(key) is False

    await limiter.record_failure(key)
    assert await limiter.is_locked_out(key) is True

    await redis.aclose()


async def test_reset_clears_the_counter(redis_url: str) -> None:
    redis = Redis.from_url(redis_url, decode_responses=True)
    limiter = RedisRateLimiter(redis, max_attempts=1, window_seconds=60)
    key = "test-lockout-key-2"

    await limiter.record_failure(key)
    assert await limiter.is_locked_out(key) is True

    await limiter.reset(key)
    assert await limiter.is_locked_out(key) is False

    await redis.aclose()
