# ADR: Payments (Stripe) (Phase 7)

## Context
Section 6 requires platform billing (Stripe Subscriptions, webhook-driven
`TenantSubscription` sync), storefront order payments (Stripe Checkout),
signature-verified/idempotent/replay-safe webhooks, and an explicit test that
replaying the same webhook event twice has no duplicate side effects.

## Decisions
- **Platform-collects-then-payout-later, not Stripe Connect** — the
  spec (Section 7) explicitly flags Connect-vs-platform-collects as a decision
  point and defaults to platform-collects for v1 simplicity. Taken as given;
  no Connect account/onboarding flow was built.
- **`UnitOfWork` gained `tenant_subscriptions` and `webhook_events`**, and
  `ProcessStripeWebhookUseCase` is built entirely around a `UnitOfWork`
  rather than individually-injected repositories. This wasn't optional: the
  Stripe webhook route is necessarily exempt from `TenantResolverMiddleware`
  (Stripe posts to one global URL, not a per-tenant subdomain), so
  `request.state.tenant_id` is never set for it, and the plain
  `get_db_session`-backed dependency never issues `SET LOCAL app.tenant_id`.
  Without a fix, every tenant-scoped query inside the webhook handler would
  silently return zero rows under RLS. The use case now calls
  `uow.set_tenant_context(tenant_id)` — extracted from the *event's own
  metadata*, not from the request — before touching `orders` or
  `tenant_subscriptions`, mirroring the same "no tenant context yet" bootstrap
  pattern `RegisterTenantOwnerUseCase` already used in Phase 2. Folding
  `webhook_events` into the same `UnitOfWork` also closes a real atomicity gap
  caught while wiring the router: an earlier draft injected `WebhookEventStore`
  as a *separate* DI dependency (its own DB session/transaction) alongside
  `uow`, meaning `mark_processed` could commit independently of the order/
  subscription mutation it's meant to guard — a crash between the two would
  leave an event marked "processed" whose actual side effect never happened.
  Now everything commits in exactly one transaction.
- **Idempotency is enforced two ways**: an application-level
  `is_processed`/`mark_processed` check (skip on replay, so a re-delivered
  event does nothing) *and* a DB-level `INSERT ... ON CONFLICT DO NOTHING`
  primary key on `event_id` (so two *simultaneously racing* deliveries of the
  same event can't both pass the `is_processed()` check and then both insert).
  `_handle_checkout_completed` additionally checks `order.status == PENDING`
  before transitioning — belt-and-suspenders against a replay somehow
  reaching the handler body despite the above.
- **`CreateSubscriptionCheckoutUseCase` pre-creates a `TenantSubscription`
  row** (status `trialing`, pointed at the chosen plan) before returning the
  Stripe Checkout URL. The alternative — resolving `plan_id` from the
  webhook's `stripe_price_id` when `customer.subscription.updated` arrives —
  would need a reverse price→plan lookup Stripe's payload doesn't hand you
  directly; pre-creating the row means the webhook only ever needs to
  *update* status/period/Stripe IDs on a record that's already scoped to the
  right plan.
- **Order payment amount uses `int(order.total * 100)`** (cents) computed
  from the already-`quantize`d `Decimal` total from Phase 6's pricing
  service — no separate currency-conversion logic needed since the platform
  is USD-only for v1.

## Consequences
- `tests/unit/infrastructure/test_stripe_gateway.py` reproduces Stripe's own
  HMAC-SHA256 webhook-signing scheme locally (timestamp + payload signed with
  the webhook secret) and calls the *real* `StripePaymentGateway` — this is
  pure crypto with no network call, so unlike every other Phase 2-7
  integration/e2e test, it actually ran in this sandboxed session (4/4
  passing) and is genuine proof the signature verification is correct, not
  just structurally plausible.
- `tests/integration/test_webhook_event_store.py` (real Postgres) and
  `tests/e2e/test_billing_flow.py` (real Postgres + Redis, `FakePaymentGateway`
  substituted via `app.dependency_overrides` so the full HTTP stack still
  never touches the real Stripe network) needed Docker and did not run here;
  they run in CI. The e2e idempotency test performs the DoD's literal check
  over real HTTP: pay → webhook (200, `"processed"`) → replay the identical
  webhook request → 200, `"already_processed"` → order status still exactly
  `paid`, not double-transitioned or errored.
