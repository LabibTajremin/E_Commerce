from redis.asyncio import Redis

from src.infrastructure.cache.redis_cache import RedisCache


async def test_set_and_get_round_trip(redis_url: str) -> None:
    redis = Redis.from_url(redis_url, decode_responses=True)
    cache = RedisCache(redis)

    await cache.set("k1", "hello", ttl_seconds=60)

    assert await cache.get("k1") == "hello"
    assert await cache.get("missing-key") is None
    await redis.aclose()


async def test_version_starts_at_zero_and_increments(redis_url: str) -> None:
    redis = Redis.from_url(redis_url, decode_responses=True)
    cache = RedisCache(redis)
    namespace = "test-namespace-unique-1"

    assert await cache.get_version(namespace) == 0

    await cache.bump_version(namespace)
    await cache.bump_version(namespace)

    assert await cache.get_version(namespace) == 2
    await redis.aclose()
