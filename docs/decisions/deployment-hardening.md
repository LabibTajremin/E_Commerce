# ADR: Deployment hardening (pre-Vercel-deploy pass)

## Context
Writing `docs/DEPLOYMENT.md` — a real step-by-step Vercel deployment guide,
not a description of one — required actually working through what happens
when the admin dashboard, storefront, and backend are deployed to three
*different* domains talking to a pooled Postgres and an S3-compatible
provider, instead of three processes on `localhost` differing only by port.
Four things that worked in dev turned out not to work at all in that
topology. This is the record of what broke and why, since none of it fit
naturally into a single phase's own ADR.

## Decisions

- **`resolveApiBaseUrl` (both frontends) only ever worked when the frontend
  and the API shared a literal hostname** — true for `acme.localhost:3000`
  vs. `acme.localhost:8000` (dev), but structurally impossible once the
  three apps live on separate real domains (`acme.myshop.com`,
  `acme.admin.myshop.com`, `acme.api.myshop.com` — none is a DNS suffix of
  either of the others). The Phase 9/10 ADRs flagged this as "a v1
  simplification, exact prod DNS layout out of scope until Phase 11" — but
  it's not a custom-domains problem (Phase 11), it's that the *existing*
  suffix-matching logic can't express the topology at all, custom domains
  or not. Fixed by dropping the suffix requirement entirely: the tenant is
  now always the hostname's *leftmost label*, spliced onto whatever
  `NEXT_PUBLIC_API_BASE_URL` is configured to, regardless of any
  relationship between the two hostnames. This is what makes the
  three-separate-wildcard-domains layout in `DEPLOYMENT.md` §2 work with
  zero backend changes.
- **asyncpg's server-side prepared-statement cache breaks under a
  transaction-mode pooler** (Neon's pooled connection string, which is the
  only sane way to point a serverless function at Postgres) —
  intermittent `DuplicatePreparedStatementError` once more than one
  request is in flight, because the pooler can hand the same physical
  connection to unrelated transactions mid-statement-cache-lifetime. Fixed
  with `connect_args={"statement_cache_size": 0}` on the engine — a no-op
  against a direct (non-pooled) connection, so this doesn't affect local
  dev or the docker-compose Postgres at all.
- **A static `CORS_ALLOWED_ORIGINS` list cannot express "every tenant's
  origin"** — each tenant has a distinct storefront and admin origin, and
  `allow_credentials=True` rules out falling back to `"*"`. Added
  `CORS_ALLOWED_ORIGIN_REGEX` (wired to Starlette's `allow_origin_regex`,
  matched in addition to the exact-match list) so production can allow
  `^https://[a-z0-9-]+\.(myshop\.com|admin\.myshop\.com)$` while local dev
  keeps using the exact-match list unchanged.
- **Cloudflare R2's S3 API endpoint doesn't serve public reads** — unlike
  AWS S3 (where the same bucket URL that objects are `PUT` to also serves
  `GET`s once the bucket policy allows it), R2 requires a *separate*
  public host (`pub-<hash>.r2.dev` or a custom domain). `S3ObjectStorage`
  was unconditionally building returned URLs from `s3_endpoint_url`, which
  would produce a URL that 403s in every visitor's browser on R2. Added
  `S3_PUBLIC_BASE_URL` (optional; falls back to the old behavior when
  unset, so AWS S3/MinIO deployments are unaffected) — and because that
  URL is inherently bucket-scoped (an R2.dev subdomain or custom domain
  maps to exactly one bucket), it's used without a bucket path segment,
  unlike the path-style `{endpoint}/{bucket}/{key}` fallback.
- **`NEXT_PUBLIC_STRIPE_PUBLIC_KEY` was required by the admin dashboard's
  env schema but never read anywhere** — a Phase 0 scaffolding leftover
  from before Phase 7 settled on server-driven Stripe Checkout redirects
  (no client-side Stripe.js/Elements). Removed rather than documented,
  since asking a deployer to supply a value nothing consumes is worse than
  not asking.
- **`vercel.json`'s `"env": {"...": "@secret_name"}` blocks (both
  frontends) were removed.** That `@`-prefixed syntax references Vercel's
  legacy Secrets feature, which Vercel itself has been sunsetting in favor
  of plain Project Environment Variables set via the dashboard — using it
  would have sent anyone following the deployment guide down a dead path.

## Consequences
- `backend/tests/unit/infrastructure/test_s3_storage.py` is new: three
  cases (path-style fallback from `s3_endpoint_url`, R2-style
  `S3_PUBLIC_BASE_URL` without a bucket segment, and the bare-AWS-S3
  fallback with neither set), mocking `aioboto3.Session.client` so it runs
  without MinIO/Docker — the existing `tests/integration/test_s3_storage.py`
  (real MinIO, needs Docker) continues to cover the original path
  end-to-end and needed no changes since its scenario (`s3_public_base_url`
  unset) still hits the same fallback branch.
- `admin-dashboard/tests/unit/apiBaseUrl.test.ts` and
  `storefront/tests/unit/apiBaseUrl.test.ts` both gained a case asserting
  the tenant label threads through even when the page and API hostnames
  share no suffix at all — the scenario that was silently broken before.
- None of this changes local development at all: `docker compose up` still
  talks to a direct (non-pooled, no RLS-pooler-adjacent behavior) Postgres,
  MinIO still serves both writes and public reads from the same endpoint,
  and `CORS_ALLOWED_ORIGIN_REGEX`/`S3_PUBLIC_BASE_URL` both default to
  unset. Every fix here is additive/backward-compatible by construction,
  not a dev-vs-prod behavioral fork to keep track of.
