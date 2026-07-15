from collections.abc import Awaitable, Callable
from uuid import UUID, uuid4

from pydantic import BaseModel

from src.presentation.caching import cached_get_or_compute
from tests.unit.application.fakes import FakeCache


class _Payload(BaseModel):
    value: int


async def _get(
    cache: FakeCache, tenant_id: UUID, key_parts: str, compute: Callable[[], Awaitable[_Payload]]
) -> _Payload:
    return await cached_get_or_compute(
        cache=cache,
        tenant_id=tenant_id,
        resource="x",
        key_parts=key_parts,
        compute=compute,
        model=_Payload,
    )


async def test_cache_miss_computes_and_stores() -> None:
    cache = FakeCache()
    tenant_id = uuid4()
    calls = 0

    async def compute() -> _Payload:
        nonlocal calls
        calls += 1
        return _Payload(value=42)

    result = await _get(cache, tenant_id, "a", compute)

    assert result.value == 42
    assert calls == 1


async def test_cache_hit_skips_recompute() -> None:
    cache = FakeCache()
    tenant_id = uuid4()
    calls = 0

    async def compute() -> _Payload:
        nonlocal calls
        calls += 1
        return _Payload(value=calls)

    first = await _get(cache, tenant_id, "a", compute)
    second = await _get(cache, tenant_id, "a", compute)

    assert first.value == second.value == 1
    assert calls == 1


async def test_bumping_version_invalidates_cache() -> None:
    cache = FakeCache()
    tenant_id = uuid4()
    calls = 0

    async def compute() -> _Payload:
        nonlocal calls
        calls += 1
        return _Payload(value=calls)

    await _get(cache, tenant_id, "a", compute)
    await cache.bump_version(f"storefront:{tenant_id}")
    second = await _get(cache, tenant_id, "a", compute)

    assert calls == 2
    assert second.value == 2


async def test_different_key_parts_do_not_collide() -> None:
    cache = FakeCache()
    tenant_id = uuid4()

    async def compute_a() -> _Payload:
        return _Payload(value=1)

    async def compute_b() -> _Payload:
        return _Payload(value=2)

    result_a = await _get(cache, tenant_id, "a", compute_a)
    result_b = await _get(cache, tenant_id, "b", compute_b)

    assert result_a.value == 1
    assert result_b.value == 2
