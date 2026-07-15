# ADR: Store Customization Engine (Phase 3)

## Context
Section 5/6 requires a `Theme` catalog with 2-3 seeded starter themes, a
per-tenant `StoreSettings` aggregate, branding update/theme-select/section-toggle
use cases, image upload via S3/MinIO, and validation for color format,
image size/type, and banner count.

## Decisions
- **`Theme` is platform-level, not tenant-scoped**: it's a shared catalog (like
  `SubscriptionPlan`), so it has no `tenant_id`/RLS — every tenant reads the
  same rows. `StoreSettings` is the tenant-scoped 1:1 aggregate (RLS, unique
  `tenant_id`), and owns its own `enabled_sections` copied from the theme's
  defaults on selection so a tenant can diverge from the theme's defaults
  without mutating the shared `Theme` row.
- **Starter themes ship as a separate data migration** (`..._seed_themes.py`)
  per Section 4.1, with fixed UUIDs so the seed is idempotent-by-inspection
  and referenceable in tests/fixtures.
- **`GetStoreSettingsUseCase` lazily creates default settings** (defaulting to
  the first seeded theme) on first access rather than requiring
  `RegisterTenantOwnerUseCase` to create them — keeps tenant registration
  (Phase 2) from having to know about theming (Phase 3), and every other
  branding use case composes `GetStoreSettingsUseCase` to get-or-create before
  mutating, so there's one lazy-init path instead of several.
- **Banner limit is a hardcoded constant** (`MAX_BANNER_IMAGES = 5` on the
  `StoreSettings` entity) raising the existing `PlanLimitExceededError`, not a
  real plan-tier lookup. Section 8 ("Plan Limits") is explicitly where
  `PlanLimitPolicy` and `SubscriptionPlan`/`TenantSubscription` enforcement
  belongs; wiring a fake single-tier plan system here would be built twice.
  Documented per Section 9.7 rather than blocking on Phase 8's scope.
- **Fixed a latent bug uncovered by this phase's color validation**: value
  objects (`ColorHex`, `Subdomain`, `Email`) raise plain `ValueError`, which
  had no handler — FastAPI's default behavior turns an unhandled `ValueError`
  into a 500, not the "clear 422" the DoD calls for. Added a
  `ValueError → 422` handler in `main.py` (distinct from the `DomainError`
  handler) so this is fixed uniformly for every current and future value
  object, not just `ColorHex`.
- **Image validation lives in the use case, not Pydantic**: content-type
  whitelist (`image/png`, `image/jpeg`, `image/webp` — deliberately excluding
  `image/svg+xml`, which can carry `<script>`/`onload` payloads) and a 5MB
  size cap are checked in `UploadStoreImageUseCase`, since they depend on the
  uploaded file's actual bytes/headers, not the request schema.

## Consequences
- `tests/integration/test_theme_repository.py` and
  `test_store_settings_repository.py` need the Postgres testcontainer (same
  as prior phases). `tests/integration/test_s3_storage.py` additionally spins
  up a `minio/minio` container via `testcontainers`' generic `DockerContainer`
  (no dedicated MinIO module exists in `testcontainers-python`, unlike
  Postgres/Redis) — none of these ran in this sandboxed session (no Docker
  daemon); they run in CI.
- `tests/e2e/test_branding_flow.py` covers the text/theme/section flows end
  to end over HTTP; it does not exercise the image-upload endpoint through
  the full HTTP stack (that would mean wiring MinIO into the shared `app`
  fixture). Image upload is covered at the use-case level (validation +
  happy path, `FakeObjectStorage`) and the storage adapter is covered against
  real MinIO in `test_s3_storage.py` — the gap is only the two wired together
  through a live HTTP multipart request, which is lower-risk than either half
  alone being untested.
