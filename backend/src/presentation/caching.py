from collections.abc import Awaitable, Callable
from typing import TypeVar
from uuid import UUID

from pydantic import BaseModel

from src.application.interfaces.cache import Cache

STOREFRONT_CACHE_TTL_SECONDS = 60
M = TypeVar("M", bound=BaseModel)


def storefront_cache_namespace(tenant_id: UUID) -> str:
    return f"storefront:{tenant_id}"


async def cached_get_or_compute(
    *,
    cache: Cache,
    tenant_id: UUID,
    resource: str,
    key_parts: str,
    compute: Callable[[], Awaitable[M]],
    model: type[M],
    ttl_seconds: int = STOREFRONT_CACHE_TTL_SECONDS,
) -> M:
    version = await cache.get_version(storefront_cache_namespace(tenant_id))
    cache_key = f"{storefront_cache_namespace(tenant_id)}:v{version}:{resource}:{key_parts}"

    cached = await cache.get(cache_key)
    if cached is not None:
        return model.model_validate_json(cached)

    result = await compute()
    await cache.set(cache_key, result.model_dump_json(), ttl_seconds)
    return result
