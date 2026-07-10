from uuid import UUID

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.category import Category
from src.domain.entities.product import Product
from src.domain.entities.store_settings import StoreSettings
from src.domain.entities.tenant import Tenant
from src.domain.entities.theme import Theme
from src.domain.repositories.product_repository import ProductFilters
from src.domain.repositories.tenant_repository import TenantFilters


class FakeTenantRepository:
    def __init__(self) -> None:
        self._tenants: dict[UUID, Tenant] = {}

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        return self._tenants.get(tenant_id)

    async def get_by_subdomain(self, subdomain: str) -> Tenant | None:
        return next((t for t in self._tenants.values() if str(t.subdomain) == subdomain), None)

    async def get_by_custom_domain(self, custom_domain: str) -> Tenant | None:
        return next(
            (t for t in self._tenants.values() if t.custom_domain == custom_domain), None
        )

    async def list(self, filters: TenantFilters) -> list[Tenant]:
        tenants = list(self._tenants.values())
        if filters.status is not None:
            tenants = [t for t in tenants if t.status == filters.status]
        if filters.search:
            needle = filters.search.lower()
            tenants = [
                t
                for t in tenants
                if needle in t.name.lower() or needle in str(t.subdomain).lower()
            ]
        return tenants[filters.offset : filters.offset + filters.limit]

    async def add(self, tenant: Tenant) -> Tenant:
        self._tenants[tenant.id] = tenant
        return tenant

    async def update(self, tenant: Tenant) -> Tenant:
        self._tenants[tenant.id] = tenant
        return tenant


class FakeAdminUserRepository:
    def __init__(self) -> None:
        self._users: dict[UUID, AdminUser] = {}

    async def get_by_id(self, tenant_id: UUID, user_id: UUID) -> AdminUser | None:
        user = self._users.get(user_id)
        return user if user and user.tenant_id == tenant_id else None

    async def get_by_email(self, tenant_id: UUID, email: str) -> AdminUser | None:
        return next(
            (
                u
                for u in self._users.values()
                if u.tenant_id == tenant_id and str(u.email) == email.strip().lower()
            ),
            None,
        )

    async def add(self, admin_user: AdminUser) -> AdminUser:
        self._users[admin_user.id] = admin_user
        return admin_user

    async def update(self, admin_user: AdminUser) -> AdminUser:
        self._users[admin_user.id] = admin_user
        return admin_user


class FakeTokenBlacklist:
    def __init__(self) -> None:
        self._revoked: set[str] = set()

    async def revoke(self, jti: str, ttl_seconds: int) -> None:
        self._revoked.add(jti)

    async def is_revoked(self, jti: str) -> bool:
        return jti in self._revoked


class FakeUnitOfWork:
    def __init__(self, tenants: FakeTenantRepository, admin_users: FakeAdminUserRepository) -> None:
        self.tenants = tenants
        self.admin_users = admin_users
        self.committed = False

    async def __aenter__(self) -> "FakeUnitOfWork":
        return self

    async def __aexit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass

    async def set_tenant_context(self, tenant_id: UUID) -> None:
        pass

    async def commit(self) -> None:
        self.committed = True

    async def rollback(self) -> None:
        pass


class FakeThemeRepository:
    def __init__(self, themes: list[Theme] | None = None) -> None:
        self._themes: dict[UUID, Theme] = {t.id: t for t in (themes or [])}

    async def get_by_id(self, theme_id: UUID) -> Theme | None:
        return self._themes.get(theme_id)

    async def list(self) -> list[Theme]:
        return list(self._themes.values())


class FakeStoreSettingsRepository:
    def __init__(self) -> None:
        self._by_tenant: dict[UUID, StoreSettings] = {}

    async def get_by_tenant(self, tenant_id: UUID) -> StoreSettings | None:
        return self._by_tenant.get(tenant_id)

    async def upsert(self, store_settings: StoreSettings) -> StoreSettings:
        self._by_tenant[store_settings.tenant_id] = store_settings
        return store_settings


class FakeObjectStorage:
    def __init__(self) -> None:
        self.uploaded: list[tuple[str, bytes, str]] = []

    async def upload(self, *, key: str, content: bytes, content_type: str) -> str:
        self.uploaded.append((key, content, content_type))
        return f"https://cdn.test/{key}"


class FakeCategoryRepository:
    def __init__(self) -> None:
        self._categories: dict[UUID, Category] = {}

    async def get_by_id(self, tenant_id: UUID, category_id: UUID) -> Category | None:
        cat = self._categories.get(category_id)
        return cat if cat and cat.tenant_id == tenant_id else None

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Category | None:
        return next(
            (
                c
                for c in self._categories.values()
                if c.tenant_id == tenant_id and str(c.slug) == slug
            ),
            None,
        )

    async def list(self, tenant_id: UUID) -> list[Category]:
        return [c for c in self._categories.values() if c.tenant_id == tenant_id]

    async def add(self, category: Category) -> Category:
        self._categories[category.id] = category
        return category

    async def update(self, category: Category) -> Category:
        self._categories[category.id] = category
        return category

    async def delete(self, tenant_id: UUID, category_id: UUID) -> None:
        cat = self._categories.get(category_id)
        if cat and cat.tenant_id == tenant_id:
            del self._categories[category_id]


class FakeProductRepository:
    def __init__(self) -> None:
        self._products: dict[UUID, Product] = {}

    async def get_by_id(self, tenant_id: UUID, product_id: UUID) -> Product | None:
        p = self._products.get(product_id)
        return p if p and p.tenant_id == tenant_id else None

    async def get_by_slug(self, tenant_id: UUID, slug: str) -> Product | None:
        return next(
            (
                p
                for p in self._products.values()
                if p.tenant_id == tenant_id and str(p.slug) == slug
            ),
            None,
        )

    async def get_by_sku(self, tenant_id: UUID, sku: str) -> Product | None:
        return next(
            (
                p
                for p in self._products.values()
                if p.tenant_id == tenant_id and p.sku and str(p.sku) == sku
            ),
            None,
        )

    def _filtered(self, tenant_id: UUID, filters: ProductFilters) -> list[Product]:
        items = [p for p in self._products.values() if p.tenant_id == tenant_id]
        if filters.category_id is not None:
            items = [p for p in items if p.category_id == filters.category_id]
        if filters.status is not None:
            items = [p for p in items if p.status == filters.status]
        if filters.min_price is not None:
            items = [p for p in items if p.price.amount >= filters.min_price]
        if filters.max_price is not None:
            items = [p for p in items if p.price.amount <= filters.max_price]
        if filters.search:
            needle = filters.search.lower()
            items = [
                p
                for p in items
                if needle in p.name.lower() or (p.description and needle in p.description.lower())
            ]
        return items

    async def count(self, tenant_id: UUID, filters: ProductFilters) -> int:
        return len(self._filtered(tenant_id, filters))

    async def add(self, product: Product) -> Product:
        self._products[product.id] = product
        return product

    async def update(self, product: Product) -> Product:
        self._products[product.id] = product
        return product

    async def delete(self, tenant_id: UUID, product_id: UUID) -> None:
        p = self._products.get(product_id)
        if p and p.tenant_id == tenant_id:
            del self._products[product_id]

    async def bulk_update_status(
        self, tenant_id: UUID, product_ids: list[UUID], status: object
    ) -> int:
        count = 0
        for pid in product_ids:
            p = self._products.get(pid)
            if p and p.tenant_id == tenant_id:
                p.status = status  # type: ignore[assignment]
                count += 1
        return count

    # Defined last: naming this `list` shadows the builtin for any annotation
    # appearing later in this class body (evaluated in the class namespace).
    async def list(self, tenant_id: UUID, filters: ProductFilters) -> list[Product]:
        items = self._filtered(tenant_id, filters)
        return items[filters.offset : filters.offset + filters.limit]


class FakeCache:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}
        self._versions: dict[str, int] = {}
        self.get_calls = 0

    async def get(self, key: str) -> str | None:
        self.get_calls += 1
        return self._values.get(key)

    async def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._values[key] = value

    async def get_version(self, namespace: str) -> int:
        return self._versions.get(namespace, 0)

    async def bump_version(self, namespace: str) -> None:
        self._versions[namespace] = self._versions.get(namespace, 0) + 1
