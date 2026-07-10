# ADR: Product Catalog (Phase 4)

## Context
Section 5/6 requires `Category`/`Product` with tenant-scoped `(tenant_id, slug)`
uniqueness, CRUD + bulk status + stock adjustment + multi-image upload with
ordering, pagination/filtering/search, and an explicit 3-tenant overlapping-slug
isolation test.

## Decisions
- **`Theme` vs. `Product`/`Category` scoping precedent carries over**: unlike
  `Theme` (platform-level), `Product`/`Category` are fully tenant-scoped with
  RLS, per Section 4's default.
- **Full-text search uses a Postgres `GENERATED ALWAYS AS ... STORED` tsvector
  column** (`search_vector`, GIN-indexed) over `name`/`description`, matching
  the spec's "Postgres full-text ... on name/description" instruction. Modeled
  in SQLAlchemy via `Computed(...)`, which is required, not cosmetic: without
  it SQLAlchemy would try to `INSERT`/`UPDATE` the column directly, and
  Postgres rejects writes to generated columns outright.
- **Indexing follows the "hottest query first" rule** the user asked for:
  `(tenant_id, status)` for "list published products" (the single hottest
  storefront query, Phase 5), `(tenant_id, category_id)` for category
  browsing, and the unique constraints on `(tenant_id, slug)` and
  `(tenant_id, sku)` double as their own lookup indexes. SKU uniqueness was
  listed in Section 4 as a per-tenant constraint but not included in the
  spec's own products-table example — added here since the spec's own
  Section 5 lists `SKU` as a `Product` field and Section 3.3 lists `SKU` as a
  value object to build.
- **A real Python-level bug surfaced by `ProductRepository`**: naming a
  Protocol/class method `list` shadows the builtin inside that class body for
  any annotation appearing *after* it (`product_ids: list[UUID]` in
  `bulk_update_status` resolved to the method, not `builtins.list`) —
  `TypeError: 'function' object is not subscriptable` at class-definition
  time, and a `mypy` "not valid as a type" error even under
  `from __future__ import annotations` (mypy resolves forward refs using the
  same class-namespace rules). Fixed by moving `list` to be the last method
  defined in `ProductRepository`, `SqlAlchemyProductRepository`, and the test
  fake — not by renaming it away from the spec's own naming (Section 3.2 names
  the method `list`).
- **SKU uniqueness is checked proactively** (`get_by_sku` before insert), the
  same pattern already used for tenant subdomains and slugs elsewhere in this
  codebase, rather than catching a DB `IntegrityError` — the latter would
  require the application layer to import a SQLAlchemy exception type,
  violating the "application depends only on repository interfaces" rule.

## Consequences
- `tests/integration/test_product_repository.py` includes the DoD's explicit
  isolation test: three tenants seeded with an identical name+slug+search
  term, then `get_by_slug`, `list`, and full-text `search` are each asserted
  to return only the calling tenant's row. Needs Docker (Postgres
  testcontainer); runs in CI, not in this sandbox.
- Product image upload/reorder reuses the same validation constants
  (allowed content types, 5MB cap) as Phase 3's store branding upload but is
  a separate use case (`UploadProductImageUseCase`) since it targets a
  `Product`'s `images` list, not `StoreSettings`; a `MAX_IMAGES_PER_PRODUCT`
  cap (10) was added for the same reason `MAX_BANNER_IMAGES` exists in Phase 3.
