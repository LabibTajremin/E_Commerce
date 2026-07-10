from types import TracebackType
from typing import Self
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.interfaces.webhook_event_store import WebhookEventStore
from src.domain.repositories.admin_user_repository import AdminUserRepository
from src.domain.repositories.cart_repository import CartRepository
from src.domain.repositories.customer_repository import CustomerRepository
from src.domain.repositories.order_repository import OrderRepository
from src.domain.repositories.product_repository import ProductRepository
from src.domain.repositories.store_settings_repository import StoreSettingsRepository
from src.domain.repositories.subscription_plan_repository import SubscriptionPlanRepository
from src.domain.repositories.tenant_repository import TenantRepository
from src.domain.repositories.tenant_subscription_repository import TenantSubscriptionRepository
from src.infrastructure.db.repositories.sqlalchemy_admin_user_repository import (
    SqlAlchemyAdminUserRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_cart_repository import SqlAlchemyCartRepository
from src.infrastructure.db.repositories.sqlalchemy_customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_order_repository import (
    SqlAlchemyOrderRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_store_settings_repository import (
    SqlAlchemyStoreSettingsRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_subscription_plan_repository import (
    SqlAlchemySubscriptionPlanRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_subscription_repository import (
    SqlAlchemyTenantSubscriptionRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_webhook_event_store import (
    SqlAlchemyWebhookEventStore,
)
from src.infrastructure.db.session import async_session_factory


class SqlAlchemyUnitOfWork:
    def __init__(self, tenant_id: UUID | None = None) -> None:
        self._tenant_id = tenant_id
        self.session: AsyncSession | None = None

    async def __aenter__(self) -> Self:
        self.session = async_session_factory()
        await self.session.begin()
        if self._tenant_id is not None:
            # SET has no bind-parameter support over the wire protocol; tenant_id is a
            # UUID instance (not raw client input), so inlining str() is injection-safe.
            await self.session.execute(text(f"SET LOCAL app.tenant_id = '{self._tenant_id}'"))
        self.tenants: TenantRepository = SqlAlchemyTenantRepository(self.session)
        self.admin_users: AdminUserRepository = SqlAlchemyAdminUserRepository(self.session)
        self.products: ProductRepository = SqlAlchemyProductRepository(self.session)
        self.customers: CustomerRepository = SqlAlchemyCustomerRepository(self.session)
        self.carts: CartRepository = SqlAlchemyCartRepository(self.session)
        self.orders: OrderRepository = SqlAlchemyOrderRepository(self.session)
        self.tenant_subscriptions: TenantSubscriptionRepository = (
            SqlAlchemyTenantSubscriptionRepository(self.session)
        )
        self.webhook_events: WebhookEventStore = SqlAlchemyWebhookEventStore(self.session)
        self.store_settings: StoreSettingsRepository = SqlAlchemyStoreSettingsRepository(
            self.session
        )
        self.subscription_plans: SubscriptionPlanRepository = SqlAlchemySubscriptionPlanRepository(
            self.session
        )
        return self

    async def set_tenant_context(self, tenant_id: UUID) -> None:
        assert self.session is not None
        self._tenant_id = tenant_id
        await self.session.execute(text(f"SET LOCAL app.tenant_id = '{tenant_id}'"))

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        assert self.session is not None
        if exc_type is not None:
            await self.session.rollback()
        await self.session.close()

    async def commit(self) -> None:
        assert self.session is not None
        await self.session.commit()

    async def rollback(self) -> None:
        assert self.session is not None
        await self.session.rollback()
