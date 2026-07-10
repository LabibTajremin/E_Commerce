from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from src.domain.repositories.admin_user_repository import AdminUserRepository
from src.domain.repositories.cart_repository import CartRepository
from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.repositories.order_repository import OrderRepository
from src.domain.repositories.product_repository import ProductRepository
from src.domain.repositories.tenant_repository import TenantRepository


class UnitOfWork(Protocol):
    tenants: TenantRepository
    admin_users: AdminUserRepository
    products: ProductRepository
    customers: CustomerRepository
    carts: CartRepository
    orders: OrderRepository

    async def __aenter__(self) -> Self: ...

    async def set_tenant_context(self, tenant_id: UUID) -> None:
        """Pin RLS's `app.tenant_id` mid-transaction, e.g. once a brand-new
        tenant row exists and subsequent inserts must be scoped to it."""
        ...

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...
