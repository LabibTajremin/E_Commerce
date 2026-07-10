from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.unit_of_work import UnitOfWork
from src.application.use_cases.billing.get_effective_plan import GetEffectivePlanUseCase
from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.exceptions import EntityNotFoundError
from src.domain.repositories.product_repository import ProductFilters


@dataclass(frozen=True, slots=True)
class TenantUsage:
    tenant_id: UUID
    plan: SubscriptionPlan
    product_count: int
    banner_count: int


class GetTenantUsageUseCase:
    def __init__(self, uow: UnitOfWork) -> None:
        self._uow = uow

    async def execute(self, tenant_id: UUID) -> TenantUsage:
        async with self._uow as uow:
            tenant = await uow.tenants.get_by_id(tenant_id)
            if tenant is None:
                raise EntityNotFoundError("Tenant", tenant_id)

            # Platform routes carry no tenant context yet (they're exempt from
            # TenantResolverMiddleware); pin RLS explicitly before touching
            # any tenant-scoped table.
            await uow.set_tenant_context(tenant_id)
            get_effective_plan = GetEffectivePlanUseCase(
                uow.subscription_plans, uow.tenant_subscriptions
            )
            plan = await get_effective_plan.execute(tenant_id)
            product_count = await uow.products.count(tenant_id, ProductFilters())
            settings = await uow.store_settings.get_by_tenant(tenant_id)
            banner_count = len(settings.banner_images) if settings else 0

        return TenantUsage(
            tenant_id=tenant_id, plan=plan, product_count=product_count, banner_count=banner_count
        )
