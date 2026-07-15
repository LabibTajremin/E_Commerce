# ADR: Storefront Frontend (Phase 10)

## Context
Section 3.5/10 requires the public storefront: per-tenant themed rendering
via CSS variables from `StoreSettings`, product listing/detail, cart,
checkout, and a Playwright e2e proving two tenant subdomains render
distinctly from the same codebase. This is the last non-bonus phase —
Phase 11 (custom domains) is the explicitly out-of-scope "stretch."

## Decisions
- **Theming is applied server-side, not client-side, to avoid a flash of
  wrong-tenant styling.** The root `layout.tsx` is a Server Component that
  reads the incoming request's Host header (`next/headers`), fetches
  `PublicStoreSettingsResponse` before any HTML is sent, and renders
  `<ThemeStyle>` — a plain server component emitting a `<style>` block with
  `--color-primary`/`--color-accent`/`--font-family` — inside `<head>`, plus
  sets `<title>`/favicon via `generateMetadata`. A client-side-only
  approach (fetch settings after mount, then set CSS variables) would
  render default/wrong colors for a beat on every load.
- **`font_choice` and the two color fields are sanitized before landing in
  a raw `<style dangerouslySetInnerHTML>` block**, even though the backend
  validates colors as hex via `ColorHex`. `font_choice` is unvalidated
  free text (`str, maxLength=100`) set by a tenant's own admin — a
  malicious or careless value could break out of the `font-family`
  declaration and inject arbitrary CSS into every visitor's browser
  (defacement, exotic CSS-based data exfiltration via attribute
  selectors). `ThemeStyle` allow-lists characters for both before
  interpolating, falling back to safe defaults otherwise; tested directly
  in `ThemeStyle.test.tsx`.
- **Same tenant-subdomain API-URL problem as the admin dashboard, solved
  twice** (client and server need different "current host" sources).
  `infrastructure/api/apiBaseUrl.ts`'s `resolveApiBaseUrl(host?)` takes an
  optional explicit host so both `httpClient.ts` (client component calls,
  `window.location.hostname`) and `serverApi.ts`'s `serverFetch` (Server
  Component calls, the incoming request's Host header via `next/headers`)
  share one implementation instead of diverging. `next.config.js` also
  needed `allowedDevOrigins: ["*.localhost"]` in both frontend apps —
  without it, Next's dev server rejects RSC/asset requests originating
  from `acme.localhost:3001` as cross-origin.
- **Cart line items only carry `product_id`/`quantity`— there's no public
  "get product by id" endpoint, only by slug** (`CartLineItemResponse` has
  no denormalized name/price snapshot). `useProductCatalog` loads the
  full published catalog once (`limit=200`, small-store-scale) and builds
  an id→product map that the cart page uses to resolve display data
  client-side, rather than changing the already-shipped Phase 6 cart
  contract.
- **Guest carts don't survive login as-is, so the frontend patches over
  it.** `get_cart_identity` (backend, Phase 6) prioritizes an authenticated
  customer's bearer token over the anonymous `X-Cart-Session-Id` header
  with no merge step — items a guest added would be silently orphaned the
  moment they register/log in at checkout. `CustomerAuthProvider` reads
  the guest cart *before* switching identity, stores the new tokens, then
  replays each line item as `POST /cart/items` under the now-authenticated
  customer. This is a client-side workaround, not a backend contract
  change (out of scope for this phase); `CustomerAuthProvider.test.tsx`
  covers it directly.
- **Checkout requires an authenticated customer (`CurrentCustomerDep`,
  no guest checkout)** — the checkout page shows a sign-in/register prompt
  instead of a shipping form when `useCustomerAuth().isAuthenticated` is
  false, and registration/login redirect back into the same flow with the
  (now-transferred) cart intact.
- **Product listing/detail pages are Server Components; cart/checkout/
  auth/orders are Client Components.** Product pages benefit from SSR
  (search-engine-facing, no user-specific state); everything past "add to
  cart" needs `localStorage` (tokens, guest session id) and interactive
  state that only makes sense client-side. `AddToCartButton` is the one
  client island embedded in an otherwise server-rendered product page.
- **No `shared/ui-primitives` reuse**, same reasoning as the Phase 9 ADR:
  no workspace wiring exists yet, and this app's needs (themed product
  cards, a cart table, an address form) don't overlap with the admin
  dashboard's config-driven `DataTable`/`FormBuilder` in a way that would
  make lifting them into `shared/` pay for itself in this pass.

## Consequences
- `npm run typecheck`, `npm run lint`, `npm run build`, and `npm test` (21
  tests: `ThemeStyle` sanitization, `ProductCard`, `AddToCartButton`,
  `useCart`'s event-driven refetch, `CustomerAuthProvider` including the
  guest-cart-transfer path, `apiBaseUrl`, plus the Phase 0 `useHealthCheck`
  test updated for the grown `ApiClient` interface) all pass with no
  Docker dependency.
- **Caught and fixed a real infinite-render-loop bug while writing
  `useCart.test.tsx`**: `renderHook(() => useCart(fakeApiClient({ get })))`
  constructs a *new* fake client object on every re-render, so `useAsync`'s
  `useCallback(fetcher, [client])` never memoizes, its
  `useEffect(() => run(), [run])` re-fires every render, and the resulting
  `setState` triggers exactly the re-render that recreates the client —
  an infinite loop that hung the whole vitest process (no timeout, no
  stack overflow, just runaway re-renders) rather than failing loudly.
  Fixed by hoisting the fake client to a variable outside the `renderHook`
  callback, and audited every other `renderHook(() => ...)` call in both
  frontend test suites for the same pattern — none of the others had it.
- Playwright is configured (`playwright.config.ts` +
  `tests/e2e/tenant-theming.spec.ts` for the two-subdomain DoD,
  `tests/e2e/shopping-flow.spec.ts` for guest→cart→register→checkout) but,
  like the admin dashboard's, not wired into CI — both need the full
  live stack. Verified in this sandbox instead: `npm run build` succeeds
  (every route reports `ƒ` / server-rendered-on-demand, correct given
  per-tenant SSR theming makes static prerendering impossible), and a
  real headless-Chromium run against `next dev` with no backend running
  confirms the app compiles/serves and fails predictably (fetch to the
  unreachable backend surfaces as a clear error, not a crash) — the
  actual happy path needs the live backend the Playwright specs target.
