# Deployment log

Append-only record of production deployments: phase, git SHA, and live URLs.

| Phase | Git SHA | Backend URL | Admin Dashboard URL | Storefront URL | Date |
|---|---|---|---|---|---|
| 0 | _pending_ | _pending — no Vercel project linked in this environment yet_ | _pending_ | _pending_ | 2026-07-05 |

> Note: this sandboxed execution environment has no Vercel account/token and no
> Docker daemon, so `vercel link` / `vercel deploy` could not be run here. The
> `vercel.json` files, `api/index.py` entrypoint, and the `deploy-preview` /
> `deploy-production` CI jobs are wired per Section 11 and are ready to run as
> soon as `VERCEL_TOKEN` (and per-project `vercel link`) are configured against
> a real Vercel account.
