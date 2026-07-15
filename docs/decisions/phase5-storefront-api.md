# ADR: Storefront Public API (Phase 5)

## Context
Section 6 requires read-only public endpoints (published products, product
detail, categories, store branding) scoped by resolved tenant, Redis response
caching invalidated on admin writes, draft products never public, and the
OpenAPI schema exported for frontend type generation.

## Decisions
- **Storefront responses are a distinct, leaner shape** (`PublicProductResponse`
  etc. in `presentation/schemas/storefront.py`), not the admin `ProductResponse`
  reused: `tenant_id`, `sku`, exact `stock_qty`, and `status` are internal
  details that shouldn't leak publicly. `stock_qty` becomes a boolean
  `in_stock`. This was caught while writing the e2e test (asserted
  `"tenant_id" not in response.json()`), not specified explicitly by the spec.
- **Cache keying uses a per-tenant version counter**, not key deletion/`SCAN`:
  `storefront:{tenant_id}:v{N}:{resource}:{key_parts}`. Any admin write that
  can affect storefront-visible data (product/category CRUD, bulk status,
  stock, image upload/reorder, all branding/theme mutations) calls
  `cache.bump_version(storefront_cache_namespace(tenant_id))`, which
  invalidates every previously-cached key for that tenant in one O(1) INCR —
  no Redis `KEYS`/`SCAN` (which blocks and doesn't scale) and no need to track
  which exact keys a write affects. Stale, orphaned entries just age out via
  TTL (60s). This is coarser than resource-specific invalidation (a product
  edit also bumps the categories/store-settings cache) but is correct and
  simple — documented as the deliberate simplification per Section 9.7.
- **Cache read/invalidate calls live in the presentation layer**
  (`presentation/caching.py`'s `cached_get_or_compute`, called from storefront
  routers; `cache.bump_version(...)` called directly from admin routers after
  a use case succeeds), not inside application use cases. Caching an HTTP
  response is a delivery-layer concern; the use cases themselves stay cache-
  unaware and are exactly the same ones Phase 3/4 already built and tested —
  Phase 5 adds no new use case for "get store branding" (reuses
  `GetStoreSettingsUseCase`) and one thin wrapper each for products/categories
  that force `status=published`.
- **A draft product 404s exactly like a nonexistent slug** — the DoD's
  requirement — enforced in `GetPublicProductBySlugUseCase`, not as an extra
  filter bolted onto the router, so the "not found vs. not published" behavior
  can't accidentally diverge between endpoints later.
- **OpenAPI export**: `backend/scripts/export_openapi.py` writes
  `shared/openapi.json` from the live `FastAPI.openapi()` call (27 paths as of
  this phase). Actual TypeScript generation (`openapi-typescript` into
  `/shared/types`) is Phase 9's concern per Section 3.3 — exporting the spec
  now unblocks that without building the frontend pipeline before there's a
  frontend to consume it.

## Consequences
- `tests/e2e/test_storefront_flow.py` includes the DoD's cache-busting test
  literally: fetch a product (cache populated) → `PATCH` it through the real
  admin endpoint → re-fetch and assert the new price is served, not the
  cached one. Needs Docker (Postgres + Redis testcontainers); runs in CI.
- Because invalidation is coarse (one namespace per tenant), a high-write
  storefront could see more cache churn than a resource-scoped scheme would
  produce. If that becomes a real bottleneck, split into
  `storefront:{tenant_id}:products`, `:categories`, `:store-settings`
  namespaces — the version-counter mechanism doesn't change, only which
  namespace each write bumps.
