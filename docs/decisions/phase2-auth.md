# ADR: Auth & Admin Users (Phase 2)

## Context
Section 4 requires transactional Tenant+AdminUser creation, JWT access/refresh
auth, revocable refresh tokens, and an explicit cross-tenant auth-leakage test.

## Decisions
- **Unit of Work**: added `application/interfaces/unit_of_work.py` (a `Protocol`
  exposing `.tenants` / `.admin_users` repositories) and its concrete
  `SqlAlchemyUnitOfWork`, per Section 3.3's "unit-of-work ... ports" note. This
  is what makes `RegisterTenantOwnerUseCase` create a `Tenant` and its owner
  `AdminUser` in one transaction without the application layer touching
  SQLAlchemy. It also gained `set_tenant_context(tenant_id)` so the *same*
  transaction can create the tenant (no RLS context yet) and then the owner row
  (which needs `app.tenant_id` set, since `admin_users` has RLS enabled).
- **RLS default-deny fix**: the Phase 1 tenants migration has no RLS (tenants
  is the root table). `admin_users`' policy uses
  `current_setting('app.tenant_id', true)::uuid` — the two-argument,
  `missing_ok=true` form — instead of the one-argument form used nowhere yet.
  Without it, any query issued while `app.tenant_id` is unset raises a hard
  Postgres error ("unrecognized configuration parameter") instead of simply
  matching zero rows. Every RLS policy from Phase 3 onward should follow this
  same two-argument form.
- **Fixed a Phase 1 bug**: `get_db_session` never committed — SQLAlchemy's
  session was opened and discarded without a `session.commit()`/`rollback()`,
  so `POST /api/v1/platform/tenants` would silently drop the tenant on
  connection close. It's now "commit on success, rollback on exception,"
  standard session-per-request. It also now issues `SET LOCAL app.tenant_id`
  from `request.state.tenant_id` (when resolved) so any tenant-scoped
  repository reached through plain `DbSession` — not just through a
  `UnitOfWork` — is RLS-covered.
- **401 vs 403**: added `AuthenticationError` (→ 401) alongside the existing
  `PermissionDeniedError` (→ 403). Bad/missing/expired/revoked credentials are
  401; a valid, authenticated caller doing something their role/tenant doesn't
  allow is 403. `get_current_admin_user`'s cross-tenant check (JWT's
  `tenant_id` claim vs. `request.state.tenant_id` from the subdomain) is the
  one deliberate 403 in the auth flow — it's an authorization refusal for an
  otherwise-valid token, exactly the case the Phase 2 DoD asks be tested
  explicitly (see `tests/unit/presentation/test_auth_dependencies.py` and
  `tests/e2e/test_auth_flow.py::test_admin_from_tenant_a_cannot_access_tenant_b_scoped_endpoint`).
- **Where tenant context comes from for login**: the admin dashboard's own
  auth flows (login) resolve tenant via the same subdomain-based
  `TenantResolverMiddleware` already built for storefront in Phase 1 (i.e.
  admin dashboard and storefront share one Host-based resolution mechanism,
  distinguished by URL path prefix, not by a separate resolution strategy).
  Post-login, authenticated admin requests trust the JWT's `tenant_id` claim
  as authoritative and only cross-check it against subdomain resolution when
  one is present, matching Section 4's "JWT claim, cross-checked against ...
  header/path if present." This is a simplification chosen for v1 scope
  (documented per Section 9.7) — Phase 11 (custom domains, out of scope here)
  would need to revisit if the admin dashboard and storefront ever need
  independent host schemes.
- **Superadmin gate (closing the Phase 1 gap)**: `platform/tenants` routes now
  require a static `X-Platform-Admin-Key` header (`require_platform_admin`),
  checked in `presentation/dependencies.py`. This is intentionally *not* the
  `AdminUser`/JWT model — a superadmin isn't a tenant owner/staff member and
  doesn't belong to any tenant, so it doesn't fit the `AdminUser` entity.
  Phase 8 ("Platform/Superadmin & Plan Limits") is where the spec scopes the
  real superadmin account/dashboard; this shared-secret header is the
  simplest option that closes the "wide open" gap until then.

## Consequences
- `tests/integration/test_admin_user_repository.py` and
  `tests/e2e/test_auth_flow.py` require Docker (Postgres *and* Redis
  testcontainers now) and could not run in this sandboxed session — same
  limitation as Phase 1, now also covering the token-blacklist round trip.
  They run in CI, which has Docker.
- `passlib[bcrypt]==1.7.4` (pinned per the spec's Section 2 tech stack) is
  unmaintained and breaks under `bcrypt>=4.1`; see `tech-stack.md` for the
  `bcrypt==4.0.1` pin this forced.
