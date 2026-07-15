# Architecture

Five diagrams, each answering a different "how does this work" question:
what's deployed where, how a request finds the right tenant, how the
backend code is organized, what the core data model looks like, and how
checkout/payment actually completes. Read [`docs/decisions/README.md`](decisions/README.md)
for *why* each of these ended up the way it did — this page is just the
shape of the system.

## 1. Deployment topology

Three separately-deployed apps sharing one Postgres/Redis/object-storage
backend, all multi-tenant by subdomain. See
[`docs/DEPLOYMENT.md`](DEPLOYMENT.md) for the full setup.

```mermaid
flowchart TB
    subgraph Browser["Browser"]
        Owner["Tenant owner"]
        Shopper["Customer"]
    end

    subgraph Vercel["Vercel"]
        AD["admin-dashboard
Next.js
*.admin.myshop.com"]
        SF["storefront
Next.js
*.myshop.com"]
        API["backend
FastAPI, single function
*.api.myshop.com"]
    end

    subgraph External["External services"]
        PG[("Postgres
Neon, pooled")]
        RD[("Redis
Upstash")]
        S3[("Object storage
S3 / R2")]
        Stripe["Stripe"]
    end

    Owner -->|"acme.admin.myshop.com"| AD
    Shopper -->|"acme.myshop.com"| SF
    AD -->|"acme.api.myshop.com"| API
    SF -->|"acme.api.myshop.com"| API
    API --> PG
    API --> RD
    API --> S3
    API <-->|"checkout + webhooks"| Stripe
```

Each tenant's slice of every wildcard domain is the *same label* —
`acme.myshop.com`, `acme.admin.myshop.com`, and `acme.api.myshop.com` are
one tenant's storefront, dashboard, and API origin respectively. The
frontends derive that third URL themselves at request time (see diagram
2) — nothing in the deployed config hardcodes a tenant.

## 2. How a request finds its tenant

There is no tenant fallback anywhere in the backend. A `Host` header that
doesn't resolve to an active tenant is a 404, on every route except the
handful (platform/superadmin, tenant registration, Stripe webhooks) that
are explicitly exempt because they aren't scoped to one tenant by nature.

```mermaid
sequenceDiagram
    participant Browser
    participant App as Frontend
    participant MW as TenantResolverMiddleware
    participant DB as Postgres

    Browser->>App: GET https://acme.myshop.com/products
    App->>MW: GET https://acme.api.myshop.com/... Host header carries acme
    MW->>DB: SELECT tenant WHERE subdomain = acme
    alt tenant found and active
        DB-->>MW: tenant row
        MW->>MW: request.state.tenant_id = tenant.id
        MW->>DB: SET LOCAL app.tenant_id = tenant uuid, then run the query
        Note over DB: RLS restricts every query to that tenant's rows
        DB-->>MW: tenant-scoped result
        MW-->>App: 200 OK
    else no match or suspended
        DB-->>MW: no row
        MW-->>App: 404 Store not found
    end
    App-->>Browser: response
```

Two independent layers of isolation, deliberately redundant:

- **Application layer**: every tenant-scoped repository query filters by
  `tenant_id` explicitly.
- **Database layer**: Postgres row-level security policies enforce the
  same filter server-side, keyed off `current_setting('app.tenant_id')`
  — so even a repository method that *forgot* the filter still can't leak
  another tenant's rows. This is what "RLS as defense in depth" (not the
  only mechanism) means in practice.

The `App` step at the top — turning `acme.myshop.com` into a request
*to* `acme.api.myshop.com` — happens client-side (or server-side during
SSR) in each frontend's `resolveApiBaseUrl()`: take the leftmost label of
whatever hostname the frontend is being viewed at, and splice it onto the
configured API host. That's what lets one frontend deployment serve every
tenant.

## 3. Backend code organization (Clean Architecture)

Dependencies point inward only: `domain/` imports nothing from any other
layer (no FastAPI, no SQLAlchemy — it's plain Python + `Protocol`s),
`application/` depends only on `domain/`, and `infrastructure/` depends on
`domain/` to *implement* its repository protocols rather than the other
way around. `presentation/dependencies.py` is the one place that knows
about concrete infrastructure classes at all — it's the composition root
that wires them into use cases via FastAPI's dependency injection.

```mermaid
flowchart TD
    subgraph Presentation["presentation/"]
        Routers["FastAPI routers"]
        DI["dependencies.py
composition root"]
    end

    subgraph Application["application/"]
        UseCases["Use cases"]
        UowProto["UnitOfWork Protocol"]
    end

    subgraph Domain["domain/ — zero framework imports"]
        EntitiesVO["Entities and value objects"]
        RepoProtocols["Repository Protocols"]
        DomainServices["Domain services
PlanLimitPolicy, pricing"]
    end

    subgraph Infrastructure["infrastructure/"]
        Concrete["SQLAlchemy repos, Redis cache,
S3 storage, Stripe gateway"]
    end

    Routers --> UseCases
    DI -. wires concrete classes into .-> UseCases
    UseCases --> RepoProtocols
    UseCases --> UowProto
    UseCases --> DomainServices
    RepoProtocols --> EntitiesVO
    Concrete -. implements .-> RepoProtocols
    Concrete -. implements .-> UowProto
```

A use case never imports a `SqlAlchemy*Repository` — it only ever sees
the `Protocol` from `domain/repositories/`, so the exact same use case
runs against a real Postgres-backed repo in production and an in-memory
fake in unit tests, with no test-only branching in application code.

## 4. Core domain model

Every box below `TENANT` (except `THEME` and `SUBSCRIPTION_PLAN`, which
are platform-level catalogs shared by every tenant) carries a `tenant_id`
and an RLS policy.

```mermaid
erDiagram
    PLATFORM_ADMIN ||--o{ TENANT : manages
    TENANT ||--o{ ADMIN_USER : employs
    TENANT ||--o{ CUSTOMER : has
    TENANT ||--o{ CATEGORY : has
    TENANT ||--o{ PRODUCT : has
    TENANT ||--o| STORE_SETTINGS : has
    TENANT ||--o| TENANT_SUBSCRIPTION : has
    THEME ||--o{ STORE_SETTINGS : "selected by"
    SUBSCRIPTION_PLAN ||--o{ TENANT_SUBSCRIPTION : "subscribed to"
    CATEGORY ||--o{ PRODUCT : contains
    CUSTOMER ||--o| CART : owns
    CUSTOMER ||--o{ ORDER : places
    CART ||--o{ CART_LINE_ITEM : contains
    PRODUCT ||--o{ CART_LINE_ITEM : "added as"
    ORDER ||--o{ ORDER_LINE_ITEM : contains
    PRODUCT ||--o{ ORDER_LINE_ITEM : "snapshotted as"

    TENANT {
        uuid id PK
        string subdomain
        string status
    }
    PRODUCT {
        uuid id PK
        uuid tenant_id FK
        string status
        int stock_qty
    }
    ORDER {
        uuid id PK
        uuid tenant_id FK
        string status
        string payment_status
    }
```

`ORDER_LINE_ITEM` deliberately *snapshots* `product_name`/`unit_price`
at checkout time rather than joining live to `PRODUCT` — an order has to
stay historically accurate even if the product is later renamed,
repriced, or deleted.

## 5. Checkout and payment

The two things worth noticing: stock is decremented under a real
row-level lock (oversell is structurally impossible, not just unlikely),
and payment completion arrives *asynchronously* via webhook, not in the
checkout request itself.

```mermaid
sequenceDiagram
    participant Customer
    participant Storefront
    participant API as Backend
    participant DB as Postgres
    participant Stripe

    Customer->>Storefront: Add to cart (guest, X-Cart-Session-Id)
    Customer->>Storefront: Register / log in at checkout
    Storefront->>API: replay guest cart items under new customer identity
    Customer->>Storefront: Submit shipping address
    Storefront->>API: POST /checkout
    API->>DB: SELECT ... FOR UPDATE (lock each product row)
    API->>DB: check stock_qty, decrement, create Order + snapshot line items
    API-->>Storefront: Order (status=pending)
    Customer->>Storefront: Pay now
    Storefront->>API: POST /orders/{id}/pay
    API->>Stripe: create Checkout Session (amount = order.total)
    Stripe-->>API: checkout_url
    API-->>Storefront: checkout_url
    Storefront-->>Customer: redirect to Stripe Checkout
    Customer->>Stripe: completes payment
    Stripe->>API: POST /webhooks/stripe (checkout.session.completed)
    API->>DB: idempotency check, set tenant context from event metadata, mark order paid
    API-->>Stripe: 200 OK
```

The webhook step is exempt from `TenantResolverMiddleware` (Stripe posts
to one global URL, not a tenant subdomain), so the tenant context RLS
needs is set explicitly from the event's own metadata rather than from
the request — see [`phase7-payments.md`](decisions/phase7-payments.md).
Idempotency is checked both in the application layer and enforced again
by a database unique constraint, so two near-simultaneous deliveries of
the same webhook event can't double-process even if they race each other
past the first check.
