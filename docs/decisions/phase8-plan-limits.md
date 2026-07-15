# ADR: Platform/Superadmin & Plan Limits (Phase 8)

## Context
Section 8 requires plan-tier limit enforcement (products, banners, custom
domains) against a tenant's current `SubscriptionPlan`, a superadmin view of
per-tenant usage vs. limits, a manual plan-override action, and closes the
Phase 1/2 gap around superadmin authentication (`require_platform_admin` was
a static shared-secret header, explicitly documented in `phase2-auth.md` as
"the simplest option that closes the wide-open gap until [Phase 8]").

## Decisions
- **`PlanLimitPolicy` is a pure domain service, not a use case** —
  `check_product_limit`/`check_banner_limit`/`check_custom_domain_allowed`
  take an already-resolved count and `SubscriptionPlan` and raise
  `PlanLimitExceededError`; no I/O. Callers (`CreateProductUseCase`,
  `UploadStoreImageUseCase`) resolve the tenant's effective plan and current
  usage themselves via the new `GetEffectivePlanUseCase`, which reads the
  tenant's `TenantSubscription` and falls back to the cheapest configured
  plan for tenants that registered but never explicitly subscribed.
- **`StoreSettings.add_banner()` lost its hardcoded `MAX_BANNER_IMAGES = 5`
  constant** (a Phase 3 placeholder, explicitly flagged then as "Phase 8's
  PlanLimitPolicy replaces this"). The domain entity is now a plain append;
  the limit check moved to `UploadStoreImageUseCase`, which is the only
  layer with access to the resolved plan.
- **Superadmin usage/override use cases go through `UnitOfWork`, not
  individually-injected repos** — `/api/v1/platform/*` routes are exempt
  from `TenantResolverMiddleware` (superadmins operate across tenants), so
  `request.state.tenant_id` is never set and the plain `get_db_session`
  dependency never issues `SET LOCAL app.tenant_id`. Without a fix, any
  tenant-scoped RLS-protected query (`products`, `store_settings`,
  `tenant_subscriptions`) issued from a platform route would silently
  return zero rows — the same class of bug fixed for the Stripe webhook
  route in Phase 7. `GetTenantUsageUseCase` and `OverridePlanUseCase` both
  call `uow.set_tenant_context(tenant_id)` (sourced from the path parameter,
  which a superadmin explicitly supplies) before touching any tenant-scoped
  table, mirroring the Phase 7 pattern. This required growing `UnitOfWork`
  with `store_settings` and `subscription_plans` repos.
- **Superadmin auth is now a real JWT-based account, not a shared secret.**
  A new `PlatformAdmin` entity/table (global, no `tenant_id`, no RLS — a
  superadmin isn't scoped to any tenant) backs `POST
  /api/v1/platform/auth/{login,refresh,logout}`, reusing the exact JWT
  machinery (`create_token`/`decode_token`, Redis token-blacklist rotation)
  tenant admins already use, distinguished by `role: "platform_superadmin"`
  and `tenant_id: null` in the token claims. `create_token`'s `tenant_id`
  parameter became `UUID | None` to support this. `require_platform_admin`
  now decodes and validates the bearer token instead of comparing a header
  to a static secret; a tenant-scoped admin token is rejected with 403 since
  its `role` claim never matches. There's deliberately no self-registration
  endpoint — `scripts/create_platform_admin.py` bootstraps the first (or an
  additional) superadmin via direct DB access, since letting anyone with API
  access mint a superadmin account would defeat the purpose of a superadmin
  gate. `PLATFORM_ADMIN_API_KEY` was removed from config/CI/`.env.example`.
- **`GetEffectivePlanUseCase` is reused for the superadmin usage view** by
  constructing it from `uow.subscription_plans`/`uow.tenant_subscriptions`
  *after* `set_tenant_context`, rather than duplicating the "resolve current
  plan" logic — the same use case object works whether it's backed by a
  request-scoped repo (tenant admin routes) or a UoW-scoped repo (platform
  routes), since both satisfy the same repository Protocols.

## Consequences
- `tests/unit/domain/test_billing.py` gained direct `PlanLimitPolicy` unit
  tests (51st product on a 50-cap plan rejected, banner cap, custom-domain
  gate) — pure functions, no fakes needed.
- `tests/unit/application/test_platform_use_cases.py` is new: exercises
  `GetTenantUsageUseCase`/`OverridePlanUseCase` against a `FakePlatformUnitOfWork`
  (single-threaded, no real RLS — the actual tenant-context-setting is proven
  by the e2e test instead, same split as every prior UoW-based use case).
- `tests/e2e/test_platform_flow.py` (real Postgres + Redis, needs Docker,
  did not run in this sandbox — runs in CI) covers: wrong-password rejected,
  a tenant-scoped admin token failing the superadmin gate (403), the
  usage/override round trip against real RLS-protected tables, and the
  explicit Phase 8 DoD check — suspending a tenant via the platform API
  immediately 404s that tenant's `/api/v1/admin/me` for an *already-issued*
  token (no re-login needed to see the effect), then reactivating restores
  access. This last one is an emergent property of Phase 1's
  `TenantResolverMiddleware` (`tenant.is_active` gate applies to `/api/v1/admin/*`
  since only `/api/v1/platform`, `/api/v1/auth`, and `/api/v1/webhooks` are
  exempt) — no new production code was needed for it, just the regression
  test the DoD calls for.
- Every existing `CreateProductUseCase(products, categories)` call site (one
  production router, six test files) needed a third `get_effective_plan`
  argument; test files use a new `unlimited_plan_use_case()` fakes.py helper
  (a `GetEffectivePlanUseCase` backed by a single very-generous plan) unless
  they're specifically testing limit-exceeded behavior.
