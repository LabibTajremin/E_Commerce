# ADR: Tenant resolution and isolation strategy (Phase 1)

## Context
Section 4 mandates shared-schema, tenant_id-discriminator multi-tenancy with
RLS as defense in depth, and tenant context must never be read from a
global/thread-local implicitly.

## Decision
- `tenants` itself is the platform-level root table — not tenant-scoped, so it
  carries no `tenant_id` column or RLS policy. Every other tenant-owned table
  (from Phase 3 onward) gets `tenant_id UUID NOT NULL` + RLS per Section 4.1.
- Indexed lookups on `tenants`: unique index on `subdomain` (the hot path hit
  on every storefront request) and unique index on `custom_domain`, plus a
  plain index on `status` for the superadmin dashboard's status filter.
- `TenantResolverMiddleware` resolves tenant by `Host` header (subdomain, then
  custom domain) for all non-platform, non-health routes, and attaches the
  result to `request.state.tenant_id` — never a thread-local/global. Platform
  (superadmin) routes are exempt since they operate across tenants.
- `UnitOfWork.begin(tenant_id)` issues `SET LOCAL app.tenant_id` at transaction
  start so future RLS policies (Phase 3+) enforce isolation even if a
  repository method forgets an explicit filter. `SET` doesn't support bind
  parameters over the wire protocol, so the UUID (already type-validated, not
  raw client input) is inlined as a string — this is documented inline as it's
  a non-obvious Postgres/asyncpg constraint, not a shortcut.

## Consequences
- Superadmin tenant CRUD (`/api/v1/platform/tenants`) currently has no auth
  gate — Phase 2 (Auth & Admin Users) adds `require_role("platform_superadmin")`
  and this endpoint must be wired to it before Phase 1 is considered
  production-ready. Tracked as the first task of Phase 2.
- Integration and e2e tests for this phase (`tests/integration/test_tenant_repository.py`,
  `tests/e2e/test_tenant_resolution.py`) require Docker (testcontainers spins up
  real Postgres) and could not be executed in this sandboxed session — only
  `tests/unit/*` (25 tests) ran here. They are wired into `.github/workflows/ci.yml`
  and will run automatically in GitHub Actions, which has Docker available.
