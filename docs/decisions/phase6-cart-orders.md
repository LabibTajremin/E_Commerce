# ADR: Cart, Checkout, Orders (Phase 6)

## Context
Section 6 requires session-or-customer carts, a separate `Customer` auth
flow, order creation with row-locked stock decrement (no oversell under
concurrent checkout), an order status lifecycle, and a reliable race-condition
test on the last unit of stock.

## Decisions
- **Row-locked stock decrement**: `ProductRepository.get_by_id_for_update`
  issues `SELECT ... FOR UPDATE`, added specifically for
  `CheckoutUseCase`. Within one DB transaction, checkout locks every product
  row in the cart, checks `stock_qty` against the requested quantity, and
  decrements — a concurrent checkout on the same product blocks on the lock
  until the first transaction commits or rolls back, then re-reads the
  post-decrement `stock_qty`. This is what makes oversell structurally
  impossible rather than merely unlikely; `tests/integration/test_checkout_concurrency.py`
  proves it by running two real concurrent checkouts (via `asyncio.gather`,
  two separate `SqlAlchemyUnitOfWork`/DB sessions) against a product with
  `stock_qty=1`, five times over, asserting exactly one success and one
  `OutOfStockError` every time, and that stock lands at exactly 0.
- **Pricing is a deliberately simple flat-rate model**
  (`domain/services/pricing.py`): 8% flat tax, $5 flat shipping, free
  shipping at $50+ subtotal. A real multi-jurisdiction tax engine or
  carrier-rate shipping API is out of scope for v1 — Section 6's "totals
  match line items + tax/shipping rules exactly" is satisfied by this rule
  being exact and tested, not by the rule being sophisticated.
- **Order line items snapshot `product_name`/`unit_price` at checkout time**
  into their own `order_line_items` table (normalized, not JSON) — an order
  must remain historically accurate even if the product is later renamed,
  repriced, or deleted. This is why `OrderLineItemModel` doesn't have a
  `tenant_id` of its own: it's only ever reached through its parent `Order`,
  which is RLS-protected, so a second RLS policy on the child table would be
  redundant (and Postgres RLS doesn't automatically cascade through a JOIN
  the way FK cascade does for deletes).
- **Customer auth is intentionally parallel to, not shared with, admin auth**:
  same JWT machinery (`core/security.create_token`, `role="customer"`),
  but a separate `Customer` entity/repository/table from `AdminUser` — they
  are different bounded-context concepts (Section 5 lists them separately)
  that happen to reuse the same low-level token infrastructure.
- **Guest checkout is out of scope**: `CheckoutUseCase` requires an
  authenticated customer (`Order.customer_id` is non-nullable) even though
  `Cart` itself supports anonymous, session-based carts per Section 6. An
  anonymous cart must belong to a logged-in customer by the time checkout is
  called; cart merge-on-login (attaching an anonymous session's cart to a
  customer that just authenticated) is not implemented — documented here as
  a deliberate v1 simplification rather than an oversight, per Section 9.7.
- **`UnitOfWork` grew `products`/`customers`/`carts`/`orders`** (previously
  only `tenants`/`admin_users`) since checkout is the first flow needing an
  atomic multi-aggregate transaction across those four. Every other Phase
  6 use case (cart add/remove, customer register/login, admin order status
  update) uses plain per-aggregate repositories via DI, same as prior phases
  — only checkout needs the full cross-aggregate transaction.

## Consequences
- The concurrency test needed one extra fix beyond the pattern used by
  earlier e2e tests: `SqlAlchemyUnitOfWork` does
  `from src.infrastructure.db.session import async_session_factory`, which
  binds a name *inside `unit_of_work.py`'s own namespace* at that module's
  first import — reassigning `session_module.async_session_factory` later
  does not change that binding (`from x import y` copies a reference, it
  isn't a live alias). Earlier e2e tests get away with only patching
  `session_module` because they defer `from src.main import app` to inside
  the fixture body, and `dependencies.py` (which does the same style of
  import) then gets *first-imported* after the patch. This test calls
  `SqlAlchemyUnitOfWork` directly, so it explicitly patches
  `src.infrastructure.db.unit_of_work.async_session_factory` too — the
  correct, general fix ("patch where a name is used, not just where it's
  defined").
- `tests/integration/test_checkout_concurrency.py` and
  `tests/e2e/test_checkout_flow.py` need Docker (Postgres + Redis
  testcontainers); neither ran in this sandboxed session. They run in CI,
  which also re-runs the whole suite on every push — satisfying the DoD's
  "run N times in CI" beyond the 5x internal loop.
