# ADR: Admin Dashboard Frontend (Phase 9)

## Context
Section 3.5/9 requires a Next.js admin dashboard: auth pages, a dashboard
shell, config-driven `DataTable`/`ListView`/`SideMenu`/`FormBuilder`
primitives, a theme customizer with live preview, product/order management
UI, a billing page, component tests, and Playwright e2e for critical flows —
reusing the Phase 0 scaffold's Clean-Architecture-flavored folder layout
(`application/interfaces`, `application/use-cases`, `infrastructure/*`).

## Decisions
- **Tenant resolution forced a design decision the scaffold hadn't made:
  where does the API base URL come from?** `TenantResolverMiddleware`
  (Phase 1) resolves the tenant from the Host header on *every*
  non-exempt backend route, including `/api/v1/admin/auth/login` itself —
  there's no fallback, a missing/unmatched subdomain is an unconditional
  404. A single hardcoded `NEXT_PUBLIC_API_BASE_URL` would therefore only
  ever work for one hardcoded tenant. `infrastructure/api/apiBaseUrl.ts`
  splices the dashboard's *own* current hostname's subdomain onto the
  configured API host at request time (`acme.localhost:3000` →
  `acme.localhost:8000`), so one dashboard deployment works for every
  tenant as long as both apps share a base domain differing only by port
  (true in dev; documented here as a v1 simplification for production,
  same spirit as the Phase 2 ADR's "Section 9.7" JWT/subdomain note — the
  exact prod DNS layout depends on final Vercel/custom-domain wiring, out
  of scope until Phase 11). Falls back to the configured URL unchanged
  when the page has no matching subdomain (e.g. plain `localhost`), which
  keeps the original single-tenant local-dev flow working unmodified.
- **Auth is a token pair in `localStorage`, not cookies** — `tokenStore`
  (get/set/clear) is a plain module, not React state, so it's readable
  from `httpClient.ts` outside any component tree. `httpClient` retries
  once through `/api/v1/admin/auth/refresh` on a 401, then dispatches a
  `window` `auth:expired` event (rather than importing the auth context,
  which would create a dependency cycle back into `AuthProvider`) that
  `AuthProvider` listens for to clear state and redirect to `/login`.
- **`layout.tsx` had to stop passing `httpClient` as a prop.** The root
  layout is a Server Component (it exports `metadata`, which Client
  Components can't do), and passing an object of functions from a Server
  Component into a Client Component (`AuthProvider`) fails at build time —
  RSC props must be serializable. `AppProviders.tsx` (a small Client
  Component) imports `httpClient` itself and wraps `AuthProvider`,
  so no function crosses the server/client boundary.
- **Primitives are config-driven, not per-page bespoke tables/forms**:
  `DataTable<T>` takes `columns: Column<T>[]` with an optional per-column
  `render`; `FormBuilder` takes `FieldConfig[]` (`text`/`number`/`textarea`
  /`select`/`checkbox`/`color`) and a flat `values`/`onChange` pair;
  `ListView` composes `DataTable` with a title, action slot, and
  prev/next pagination; `SideMenu` takes `NavItem[]` and highlights the
  active route via `usePathname`. Every list/form page (products,
  categories, orders, branding sections) is a thin composition of these
  four, not a bespoke table/form each.
- **The branding page's "live preview" reflects in-memory form state, not
  the saved `StoreSettings`** — color/font/store-name inputs are bound to
  local component state that's only persisted on explicit Save; the
  preview panel binds the same state to CSS custom properties
  (`--preview-primary`, etc.) so edits are visible before saving, matching
  the spec's "live preview" requirement without a round trip per keystroke.
- **CSS Modules, no Tailwind** — the Phase 0 scaffold has neither
  Tailwind nor any CSS framework configured, and adding one is orthogonal
  to Phase 9's actual deliverables. Plain CSS custom properties in
  `globals.css` (`--color-primary`, `--spacing-*`, etc.) plus one CSS
  Module per component/page keeps styling co-located and typed without a
  new build-tool dependency.
- **`shared/ui-primitives/` (an empty Phase 0 placeholder) was not used.**
  There's no npm/pnpm workspace linking `admin-dashboard`, `storefront`,
  and `shared` together yet (`shared/package.json` exists but nothing
  depends on it, and neither app's `next.config.js` has
  `transpilePackages` set up for consuming a workspace TSX package).
  Wiring a real workspace now — for primitives Phase 10's storefront may
  not even need in the same shape (admin CRUD tables/forms vs. public
  product/cart pages) — was judged disproportionate scope for this phase;
  primitives live under `admin-dashboard/src/presentation/components/
  primitives/` and can be lifted into `shared/` with real workspace wiring
  if Phase 10 turns out to need the same ones verbatim.
- **Playwright is configured but not wired into CI.** `playwright.config.ts`
  + `tests/e2e/product-management.spec.ts` (login → create product → see
  it in the list, tenant/owner provisioned via a direct API call since
  there's no registration UI) require the full stack live — backend +
  Postgres + Redis + this app's dev server — the same Docker dependency
  that already keeps the backend's integration/e2e suites out of this
  sandbox. `npm run test:e2e` runs it once that stack exists; `ci.yml`'s
  `frontend-test` job still only runs `lint` + `vitest`.

## Consequences
- `npm run typecheck`, `npm run lint`, `npm run build`, and `npm test`
  (21 tests across `DataTable`, `FormBuilder`, `SideMenu`, `AuthProvider`,
  `useProductList`, `resolveApiBaseUrl`, plus the Phase 0
  `useHealthCheck` test updated for the grown `ApiClient` interface) all
  pass in this sandbox — no Docker dependency for any of them.
- Manually verified in a real browser (Playwright against the dev
  server, no backend running): `/login` renders and is styled correctly;
  submitting invalid credentials shows an inline error instead of
  crashing; visiting `/` while unauthenticated redirects to `/login`
  (`RequireAuth`). The full login → CRUD flow needs the live backend the
  Playwright spec targets and could not be exercised end-to-end here.
- `tests/unit/fakeApiClient.ts` is a small shared test double
  implementing the full `ApiClient` interface (each method throws
  "not implemented" unless overridden) so hook/provider tests only stub
  the methods they actually exercise.
