# Decision log

This is the running record of what got built, in what order, and — more
importantly — *why* it ended up the way it did: the tradeoffs taken,
the bugs a given phase's own work surfaced (often in an *earlier* phase),
and what was deliberately left simpler than a "real" production system
would need. Each phase has its own ADR with full detail; this page is the
index and the connective tissue between them, since a lot of the more
interesting decisions are things one phase's work exposed about a
previous phase's assumptions, not clean isolated choices.

Read in order — later phases assume earlier ones happened, and several
entries below only make sense as "we thought X in phase N, phase M proved
that wrong."

| Phase | ADR | What it covers |
|---|---|---|
| 0 | *(scaffolding, no dedicated ADR)* | Monorepo layout, pinned dependency versions — see [`tech-stack.md`](./tech-stack.md) |
| 1 | [`phase1-tenants.md`](./phase1-tenants.md) | Tenant isolation strategy: shared-schema + RLS, subdomain resolution middleware |
| 2 | [`phase2-auth.md`](./phase2-auth.md) | JWT auth, Unit of Work, the RLS "unset config parameter" trap |
| 3 | [`phase3-theming.md`](./phase3-theming.md) | Theme vs. StoreSettings split, lazy defaults, the `ValueError→422` fix |
| 4 | [`phase4-product-catalog.md`](./phase4-product-catalog.md) | Full-text search, indexing strategy, the `list`-shadows-builtin bug |
| 5 | [`phase5-storefront-api.md`](./phase5-storefront-api.md) | Public response shapes, version-counter cache invalidation |
| 6 | [`phase6-cart-orders.md`](./phase6-cart-orders.md) | Row-locked checkout (oversell-proof), flat-rate pricing, order snapshotting |
| 7 | [`phase7-payments.md`](./phase7-payments.md) | Stripe Checkout, webhook idempotency, the tenant-context-under-webhooks fix |
| 8 | [`phase8-plan-limits.md`](./phase8-plan-limits.md) | Plan-tier enforcement, real superadmin auth (replacing a shared secret) |
| 9 | [`phase9-admin-dashboard.md`](./phase9-admin-dashboard.md) | Admin dashboard architecture, config-driven UI primitives |
| 10 | [`phase10-storefront.md`](./phase10-storefront.md) | Server-side per-tenant theming, guest-cart-to-customer handoff |
| — | [`deployment-hardening.md`](./deployment-hardening.md) | What broke turning this into a real Vercel deployment, and why |
| — | [`deployment-log.md`](./deployment-log.md) | Append-only record of actual deployed URLs, by phase and git SHA |
| — | [`master-password.md`](./master-password.md) | Break-glass superadmin login: the risk, why it was built anyway, and its mitigations |

Phase 11 (custom domains) was scoped in the original spec as a stretch
goal and was left unbuilt — see "What's out of scope" below.

## The throughline: tenant context is the recurring bug

The single decision made in Phase 1 — resolve the tenant from the `Host`
header into `request.state.tenant_id`, never a thread-local/global — is
correct and never changed. But **every place that bypasses the normal
per-request path has had to re-derive tenant context by hand**, and each
phase that introduced one of those places found a bug in it:

1. **Phase 2**: `admin_users`' RLS policy used the *one-argument* form of
   `current_setting('app.tenant_id')`, which raises a hard Postgres error
   the instant `app.tenant_id` is unset, instead of just matching zero
   rows. Fixed with the two-argument `missing_ok=true` form — the pattern
   every RLS policy since has followed.
2. **Phase 2** (same phase, different bug): `get_db_session` never called
   `session.commit()` at all — a Phase 1 bug that had been silently
   dropping every write since `POST /api/v1/platform/tenants` was first
   built, only caught once Phase 2 needed to prove auth worked end-to-end.
3. **Phase 7**: Stripe posts webhooks to one global URL, not a tenant
   subdomain — so `TenantResolverMiddleware` is exempt for that route, so
   `request.state.tenant_id` is never set, so RLS silently returns zero
   rows for every tenant-scoped query in the handler unless something else
   sets it. Fixed by having `ProcessStripeWebhookUseCase` pull the tenant
   from the *event's own metadata* and call `uow.set_tenant_context(...)`
   explicitly before touching anything RLS-protected.
4. **Phase 8**: the same exemption applies to `/api/v1/platform/*`
   (superadmins operate across tenants by design) — so the new tenant-usage
   and plan-override endpoints hit the exact same silent-empty-result trap,
   fixed the same way, this time sourcing the tenant from the path
   parameter a superadmin explicitly supplies.
5. **Deployment hardening** (post-Phase-10): the frontends' own
   "which tenant am I" resolution (derived from *their own* hostname, not
   the backend's) turned out to only work when frontend and backend shared
   a literal hostname — true by accident in local dev, false the moment
   they're on three separate production domains. Same root shape of bug —
   an implicit assumption about how tenant context gets threaded through,
   invisible until the topology it was implicitly relying on changed.

None of these were caught by the phase that introduced the pattern; every
one was caught by the *next* phase (or the deployment pass) that exercised
it under slightly different conditions. That's a fair summary of how this
project actually got built: not "get it right once," but "the next phase
is also a regression test for the last one."

## Other decisions that recur across phases

- **`UnitOfWork` grew by need, not by upfront design.** It started
  (Phase 2) with just `tenants`/`admin_users`, because that's what
  `RegisterTenantOwnerUseCase`'s single transaction needed. Every phase
  since added exactly the repos its own cross-aggregate transaction
  needed (`products`/`customers`/`carts`/`orders` in Phase 6,
  `tenant_subscriptions`/`webhook_events` in Phase 7, `store_settings`/
  `subscription_plans` in Phase 8) — never spec'd out in full ahead of
  time. The alternative (designing the complete `UnitOfWork` interface in
  Phase 2 for repos that wouldn't exist until Phase 8) would have meant
  guessing at needs six phases early.
- **Every plain `ValueError` from a domain value object (`ColorHex`,
  `Subdomain`, `Email`, `Slug`, `SKU`) is a 422, uniformly, via one handler
  in `main.py`** — added when Phase 3's `ColorHex` validation exposed that
  invalid input was surfacing as a 500 with no handler, fixed once for
  every value object rather than one at a time as each got exercised.
- **Money and time are always exact, never "roughly right."** Order totals
  are computed once at checkout and snapshotted (Phase 6) rather than
  recomputed from live product prices later; webhook idempotency is
  enforced at both the application layer (`is_processed` check) and the
  database layer (`INSERT ... ON CONFLICT DO NOTHING`) so a race between
  two simultaneous webhook deliveries can't double-process even if the
  application-layer check itself races (Phase 7).
- **Simplifications are named, not hidden.** Flat 8% tax / $5 shipping
  instead of a real tax/shipping engine (Phase 6), platform-collects
  instead of Stripe Connect (Phase 7), plain CSS Modules instead of a
  design-system dependency (Phase 9/10) — each is called out in its ADR
  as a deliberate v1 scope cut, with the reason, rather than left for a
  future reader to guess whether it was an oversight or a choice.

## What's deliberately out of scope

- **Phase 11 — custom domains.** The spec names this a stretch goal.
  Tenants get a subdomain (`acme.myshop.com`); mapping an arbitrary
  domain a tenant owns (`shop.acme.com`) onto their store — DNS
  verification, per-domain TLS — was not built. `tenants.custom_domain`
  exists as a column and `TenantResolverMiddleware` already checks it as
  a fallback after subdomain matching, but nothing populates or verifies
  it.
- **Stripe Connect / marketplace payouts** (Phase 7) — the platform
  collects all payments directly; there's no per-tenant Stripe account,
  onboarding flow, or automated payout split.
- **A real tax/shipping engine** (Phase 6) — flat rate, not
  jurisdiction-aware or carrier-rate-integrated.
- **`shared/ui-primitives`** was scaffolded in Phase 0 but never
  populated — no npm/pnpm workspace links `admin-dashboard`, `storefront`,
  and `shared` together, and neither app's `next.config.js` has
  `transpilePackages` configured for it. The admin dashboard's
  `DataTable`/`FormBuilder`/`SideMenu`/`ListView` primitives live under
  `admin-dashboard/src/presentation/components/primitives/` instead;
  see the Phase 9 and 10 ADRs for the reasoning.
- **Celery** is a pinned dependency (per the original tech-stack spec) but
  nothing in the app enqueues a task — there's no background job that
  needed one yet. Not deployed or run anywhere.
- **Cart merge across the guest→login boundary is a client-side patch,
  not a backend contract change** — see the Phase 10 ADR. The backend's
  cart-identity resolution prioritizes an authenticated customer's token
  over a guest session id with no merge step; the storefront frontend
  works around it by replaying the guest cart's line items after login
  rather than the backend gaining a "merge carts" endpoint.
