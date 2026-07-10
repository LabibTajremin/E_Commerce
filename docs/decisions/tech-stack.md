# ADR: Tech stack and pinned versions

## Context
Project init requires pinning exact versions per the platform spec (Section 2) so
builds are reproducible across dev, CI, and Vercel.

## Decision
- Backend: Python 3.12, FastAPI 0.115.6, SQLAlchemy 2.0.36 (async) + asyncpg 0.30.0,
  Alembic 1.14.0, Pydantic 2.10.4 / pydantic-settings 2.7.1, python-jose 3.3.0,
  passlib[bcrypt] 1.7.4, redis-py 5.2.1, Celery 5.4.0, boto3 1.35.90, stripe-python
  11.4.1, structlog 24.4.0. Dev/test: pytest 8.3.4, pytest-asyncio 0.25.0,
  testcontainers 4.9.0, polyfactory 2.18.1, ruff 0.8.4, mypy 1.14.0.
- Frontend (admin-dashboard, storefront): Next.js 15.5.20 (patched; 15.1.3 as specified
  in the original brief carries CVE-2025-66478 — see Consequences), React 19, TypeScript
  5.7.2, Zod 3.24.1, Vitest 3.2.6 (2.1.8 as originally scoped had a critical RCE
  advisory in its Vite dependency chain), Testing Library 16.1.0.
- Database: PostgreSQL 16 (via `postgres:16-alpine` in docker-compose / testcontainers).

- Object storage uses `aioboto3==13.3.0` rather than plain `boto3` (still listed
  in Section 2). The app is async-first end to end (async SQLAlchemy, async
  routes); calling synchronous `boto3` from an `async def` route would block
  the event loop. `aioboto3` wraps `boto3`/`aiobotocore` with an async client
  and works identically against MinIO via `endpoint_url`, so this is a
  same-tech, async-compatible substitution rather than a stack change.
- `bcrypt` is pinned to `4.0.1` explicitly. `passlib[bcrypt]==1.7.4` is unmaintained
  and probes `bcrypt.__about__` at import time, an attribute `bcrypt>=4.1` removed;
  without the pin, every `hash_password`/`verify_password` call raises. `4.0.1` is
  the newest release that still exposes it.

## Consequences
- Two library versions deviate from the literal versions implied by the spec's
  examples (Next.js, Vitest) because the originally-implied minor versions have
  disclosed critical/high-severity CVEs. Patched versions in the same major line
  were selected to keep the architecture unchanged.
- `requires-python = ">=3.12"` in `backend/pyproject.toml` enforces the runtime
  floor; CI pins `actions/setup-python@v5` to `3.12`.
- Re-run `npm audit` / `pip list --outdated` at the start of each phase and update
  this ADR if further CVE-driven version bumps are needed.
