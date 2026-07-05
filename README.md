# E_Commerce

Multi-tenant e-commerce SaaS platform. See the full implementation spec discussion
and architecture decisions in `docs/decisions/`.

## Structure

- `backend/` — FastAPI + SQLAlchemy (async) + Alembic, Clean Architecture layers
  (`domain/`, `application/`, `infrastructure/`, `presentation/`).
- `admin-dashboard/` — Next.js app for tenant owners.
- `storefront/` — Next.js app for end customers.
- `shared/` — cross-app TypeScript types and UI primitives, imported explicitly.

## Local development

```bash
# Backend
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in secrets
alembic upgrade head
uvicorn src.main:app --reload

# Admin dashboard
cd admin-dashboard
cp .env.example .env.local
npm install && npm run dev   # http://localhost:3000

# Storefront
cd storefront
cp .env.example .env.local
npm install && npm run dev   # http://localhost:3001
```

Or boot the whole stack (API + Postgres + Redis + MinIO) with:

```bash
docker compose up
```

## Testing

```bash
cd backend && pytest                 # unit + integration + e2e (Docker required for the latter two tiers)
cd admin-dashboard && npm run test
cd storefront && npm run test
```
