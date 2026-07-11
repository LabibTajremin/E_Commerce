# Deploying the MVP to Vercel

This walks through a small-scale but fully-featured production deployment:
every phase's functionality works (tenants, auth, catalog, storefront, cart,
checkout, Stripe billing, superadmin), sized for a handful of tenants rather
than a fleet.

## 1. Architecture recap

Three deployables, one shared Postgres/Redis/object-storage backend:

- **`backend/`** — FastAPI, deployed as a single Vercel Function
  (`@vercel/python`, `api/index.py` wraps the ASGI app).
- **`admin-dashboard/`** — Next.js, tenant admins sign in here.
- **`storefront/`** — Next.js, public-facing, one instance serves every
  tenant's storefront.

All three are **multi-tenant by subdomain**: the backend resolves which
tenant a request belongs to from the `Host` header
(`TenantResolverMiddleware`), and there is no fallback — an unresolvable
subdomain is a 404. That means all three apps need **wildcard domains**, and
the domain layout matters (see §2) — it's not just "add a custom domain and
go."

## 2. Domain layout

You need one domain you control (e.g. `myshop.com`). This guide uses three
wildcarded subdomains under it — pick different labels if you like, but keep
the *shape* (tenant label is always the leftmost part of the hostname):

| App | Domain to add in Vercel | Example tenant URL |
|---|---|---|
| Storefront | `*.myshop.com` (+ bare `myshop.com`) | `acme.myshop.com` |
| Admin dashboard | `*.admin.myshop.com` | `acme.admin.myshop.com` |
| Backend API | `*.api.myshop.com` (+ bare `api.myshop.com`) | `acme.api.myshop.com` |

Why it has to be wildcarded per app, not just one wildcard total: Vercel
routes each hostname to exactly one project, so the storefront, dashboard,
and API each need their own slice of DNS. The frontends derive the
per-tenant API origin at request time (`resolveApiBaseUrl` in both apps) by
taking the leftmost label of their own hostname and combining it with
whatever bare host you configure as `NEXT_PUBLIC_API_BASE_URL` — so as long
as each app's own domain is wildcarded, the tenant threads through correctly
regardless of how different the three domains otherwise look.

**DNS setup**: wildcard domains on Vercel require Vercel to manage DNS for
the zone (it needs to answer ACME challenges for the wildcard TLS cert). At
your registrar, point `myshop.com`'s nameservers to:

```
ns1.vercel-dns.com
ns2.vercel-dns.com
```

This is supported on Vercel's free Hobby plan — no paid plan required for
wildcard domains themselves.

## 3. Provision external services

Vercel Functions are stateless/short-lived, so the database, cache, and
object storage all need to be separately-hosted, connection-pool-friendly
services. Recommended picks for MVP scale (all have usable free tiers):

### 3a. Postgres — [Neon](https://neon.tech)

1. Create a project, default database is fine.
2. Copy the **pooled** connection string (the one with `-pooler` in the
   hostname) — this routes through PgBouncer in transaction mode, which is
   what makes Postgres usable from serverless functions without exhausting
   connections. Direct (non-pooled) connections will work for occasional
   scripts (migrations, seeding) but shouldn't be what the deployed app uses.
3. This is `DATABASE_URL`, reformatted for SQLAlchemy's async driver:
   `postgresql+asyncpg://<user>:<password>@<pooled-host>/<db>?sslmode=require`

   > The app disables asyncpg's server-side prepared-statement cache
   > (`connect_args={"statement_cache_size": 0}` in
   > `backend/src/infrastructure/db/session.py`) specifically so it's safe
   > against a transaction-mode pooler like this — without it you'd hit
   > `DuplicatePreparedStatementError` under any concurrent load.

### 3b. Redis — [Upstash](https://upstash.com)

1. Create a Redis database (regional, closest to your Vercel deployment
   region).
2. Copy the `rediss://` (TLS) connection string — this is `REDIS_URL`.
   Used for the JWT revocation blacklist and storefront response caching.

### 3c. Object storage — AWS S3 *or* Cloudflare R2

Either works out of the box; R2 has no egress fees, S3 has fewer moving
parts for a first deploy. Product/logo/banner images go here.

**AWS S3** (simpler — public bucket URL doubles as the API endpoint):
1. Create a bucket, enable public read access (bucket policy allowing
   `s3:GetObject` for `*`), disable "Block all public access" for it.
2. Create an IAM user with `s3:PutObject`/`s3:GetObject` on that bucket only,
   generate an access key.
3. Env vars: `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`,
   `S3_REGION=<bucket-region>`. Leave `S3_ENDPOINT_URL` and
   `S3_PUBLIC_BASE_URL` unset.

**Cloudflare R2**:
1. Create a bucket. Under its Settings, enable **public access** (the
   `pub-<hash>.r2.dev` URL, or attach a custom domain) — R2's S3 API
   endpoint does *not* itself serve public reads, so this step is required
   or uploaded images will 403 in browsers.
2. Create an R2 API token (Account API token, object read/write, scoped to
   this bucket).
3. Env vars: `S3_ENDPOINT_URL=https://<account_id>.r2.cloudflarestorage.com`,
   `S3_REGION=auto`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, and
   `S3_PUBLIC_BASE_URL=https://pub-<hash>.r2.dev` (or your custom domain).

### 3d. Stripe

1. Use **test mode** keys for an MVP unless you're taking real payments.
2. Note `STRIPE_SECRET_KEY` (`sk_test_...`) — the webhook secret comes in
   §6 after the backend has a public URL to register a webhook against.
3. In the Stripe dashboard, create the subscription Products/Prices you
   want tenants to pick from — but for MVP scale it's simpler to skip this
   and rely on the `subscription_plans` seeded by the migrations (Starter/
   Growth/Scale — see `202607052401_phase7_seed_subscription_plans.py`),
   which don't require matching Stripe Price objects for the plan-limit
   enforcement itself to work; they're only needed if you want the
   "Subscribe" button in the dashboard to reach a real Stripe Checkout
   Session for a *recurring* subscription (order payments work regardless,
   since those create a Checkout Session per-order from the order total).

## 4. Deploy the backend

From the Vercel dashboard: **New Project** → import the repo → set **Root
Directory** to `backend`. It'll pick up `backend/vercel.json`
(`@vercel/python`, `api/index.py`) automatically.

**Environment variables** (Project Settings → Environment Variables; set for
Production and Preview):

```
DATABASE_URL=postgresql+asyncpg://...neon pooled connection...
REDIS_URL=rediss://...upstash...
JWT_SECRET=<openssl rand -hex 32>
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...           # from §6, can set after first deploy
S3_BUCKET=...
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=...
S3_ENDPOINT_URL=...                        # R2 only
S3_PUBLIC_BASE_URL=...                     # R2 only
CORS_ALLOWED_ORIGIN_REGEX=^https://[a-z0-9-]+\.(myshop\.com|admin\.myshop\.com)$
PLATFORM_BASE_DOMAIN=api.myshop.com
TAX_RATE=0.08                              # flat-rate tax/shipping, see §10's decisions link
FLAT_SHIPPING_FEE=5.00
FREE_SHIPPING_THRESHOLD=50.00
MASTER_PASSWORD_HASH=...                   # optional — see "Optional: enable the master password" below
```

Deploy. Then, under the project's **Domains**, add both `api.myshop.com` and
`*.api.myshop.com`.

## 5. Run migrations and bootstrap data

Vercel Functions can't run one-off scripts, so do this from your machine
(or a CI job) pointed at the **direct** (non-pooled) Neon connection string —
migrations run DDL, which some poolers handle poorly; a direct connection
avoids that entirely:

```bash
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

export DATABASE_URL="postgresql+asyncpg://...neon DIRECT (non-pooled) connection..."
alembic upgrade head          # creates every table, RLS policy, and seeds
                               # starter themes + subscription plans

python scripts/create_platform_admin.py --email you@example.com
python scripts/seed_demo_data.py --subdomain demo --owner-email owner@demo.example
```

`alembic upgrade head` is the entire "create the database from scratch"
step — every table, index, and Postgres row-level-security policy across
all 10 migrations runs in order from an empty database; nothing manual is
needed beyond having `DATABASE_URL` point at that empty database. The two
scripts after it are optional but recommended for an MVP: the first gives
you a superadmin login for `/api/v1/platform/*`; the second creates a demo
tenant (`demo`) with two categories and six published products so there's
something to click through immediately after deploying the frontends.

### Optional: enable the master password

Off by default. If you want a single break-glass credential that can log
into any account (tenant admin, customer, or platform superadmin) — see
[`docs/decisions/master-password.md`](./decisions/master-password.md) for
what this is and the risk it carries before turning it on — generate a
hash and add it to the backend's environment variables:

```bash
python scripts/hash_master_password.py
# prompts for the password twice, prints:
# MASTER_PASSWORD_HASH=$2b$12$...
```

Add that line (and, optionally, `MASTER_PASSWORD_MAX_ATTEMPTS` /
`MASTER_PASSWORD_LOCKOUT_WINDOW_SECONDS` to change the default 5-attempts-
per-15-minutes lockout) to the backend Vercel project's environment
variables, then redeploy. Review who used it via
`GET /api/v1/platform/master-password-usages` (superadmin bearer token
required).

## 6. Configure the Stripe webhook

In the Stripe dashboard → Developers → Webhooks → **Add endpoint**:

- URL: `https://api.myshop.com/api/v1/webhooks/stripe` (this route is
  exempt from tenant-subdomain resolution — Stripe posts to one global URL
  and the tenant is read from the event's own metadata instead)
- Events: `checkout.session.completed`, `customer.subscription.updated`,
  `customer.subscription.deleted`

Copy the signing secret it gives you into `STRIPE_WEBHOOK_SECRET` on the
backend Vercel project, then redeploy (env var changes need a redeploy to
take effect on Vercel).

## 7. Deploy the admin dashboard

**New Project** → same repo → **Root Directory**: `admin-dashboard`.

Environment variable:

```
NEXT_PUBLIC_API_BASE_URL=https://api.myshop.com
```

Deploy, then add domain `*.admin.myshop.com` under Domains.

## 8. Deploy the storefront

**New Project** → same repo → **Root Directory**: `storefront`.

Environment variable:

```
NEXT_PUBLIC_API_BASE_URL=https://api.myshop.com
```

Deploy, then add domains `*.myshop.com` and bare `myshop.com` under Domains.

## 9. Smoke test

1. `https://demo.myshop.com` — storefront loads with the demo tenant's
   name/theme, product grid shows the six seeded products.
2. `https://demo.admin.myshop.com/login` — sign in with the demo owner
   credentials from §5, confirm the products/categories/orders pages load.
3. Add a product to cart on the storefront as a guest, register a customer
   account at checkout, place an order — confirm it appears under both
   `/orders` on the storefront and `/orders` in the admin dashboard.
4. `https://api.myshop.com/health` → `{"status": "ok"}`.
5. `https://api.myshop.com/docs` — Swagger UI, confirms the exempt
   platform/auth/webhook routes aren't blocked by tenant resolution.
6. Suspend the demo tenant via a superadmin call (`POST
   /api/v1/platform/tenants/{id}/suspend` with the platform admin token from
   §5) and confirm `demo.admin.myshop.com` immediately 404s.

## 10. Cost at this scale

Everything above fits comfortably in the free tiers of Vercel (Hobby),
Neon, Upstash, and Cloudflare R2/AWS S3's free allowance, plus Stripe test
mode being free. The only recurring cost is the domain registration itself.
This scales to real traffic by moving to Vercel Pro and the paid tiers of
the same three services — no architecture change required.

## Troubleshooting

- **Every request 404s "Store not found"**: the `Host` header didn't
  resolve to a tenant. Check `PLATFORM_BASE_DOMAIN` matches what you
  wildcarded, and that the tenant's `subdomain` column matches the label
  you're browsing to.
- **CORS errors in the browser console**: `CORS_ALLOWED_ORIGIN_REGEX` has
  to match the *exact* Origin the browser sends (scheme + host, no path) —
  double check it against the failing request's Origin header, and that a
  backend redeploy happened after setting it.
- **Images upload but don't load**: on R2, confirm the bucket's public
  access is enabled and `S3_PUBLIC_BASE_URL` is set — the R2 API endpoint
  alone does not serve public reads.
- **Intermittent 500s under any concurrent load, Postgres-related**: almost
  always means `DATABASE_URL` is pointed at a pooled connection but
  `statement_cache_size: 0` isn't taking effect — confirm you're running
  the version of `backend/src/infrastructure/db/session.py` that sets it.
