from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.use_cases.billing.get_tenant_usage import GetTenantUsageUseCase
from src.application.use_cases.billing.override_plan import (
    OverridePlanInput,
    OverridePlanUseCase,
)
from src.application.use_cases.products.create_product import (
    CreateProductInput,
    CreateProductUseCase,
)
from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.entities.tenant import Tenant
from src.domain.entities.tenant_subscription import SubscriptionStatus, TenantSubscription
from src.domain.exceptions import EntityNotFoundError
from src.domain.value_objects.money import Money
from src.domain.value_objects.subdomain import Subdomain
from tests.unit.application.fakes import (
    FakeCategoryRepository,
    FakePlatformUnitOfWork,
    FakeProductRepository,
    FakeStoreSettingsRepository,
    FakeSubscriptionPlanRepository,
    FakeTenantRepository,
    FakeTenantSubscriptionRepository,
    unlimited_plan_use_case,
)


def _plan(**overrides: object) -> SubscriptionPlan:
    defaults: dict[str, object] = {
        "name": "Growth",
        "price": Money(Decimal("29.00")),
        "max_products": 50,
        "max_banners": 5,
        "custom_domain_allowed": False,
    }
    defaults.update(overrides)
    return SubscriptionPlan(**defaults)  # type: ignore[arg-type]


async def test_get_tenant_usage_reports_product_count_against_plan() -> None:
    tenant = Tenant(name="Acme", subdomain=Subdomain("acme"))
    tenants = FakeTenantRepository()
    await tenants.add(tenant)
    plan = _plan(max_products=2)
    plans = FakeSubscriptionPlanRepository([plan])
    subscriptions = FakeTenantSubscriptionRepository()
    await subscriptions.upsert(TenantSubscription(tenant_id=tenant.id, plan_id=plan.id))
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    await CreateProductUseCase(products, categories, unlimited_plan_use_case()).execute(
        CreateProductInput(tenant_id=tenant.id, name="Widget", price=Decimal("1"))
    )
    store_settings = FakeStoreSettingsRepository()

    uow = FakePlatformUnitOfWork(tenants, products, store_settings, plans, subscriptions)
    usage = await GetTenantUsageUseCase(uow).execute(tenant.id)

    assert usage.product_count == 1
    assert usage.banner_count == 0
    assert usage.plan.id == plan.id


async def test_get_tenant_usage_raises_for_unknown_tenant() -> None:
    uow = FakePlatformUnitOfWork(
        FakeTenantRepository(),
        FakeProductRepository(),
        FakeStoreSettingsRepository(),
        FakeSubscriptionPlanRepository(),
    )
    with pytest.raises(EntityNotFoundError):
        await GetTenantUsageUseCase(uow).execute(uuid4())


async def test_override_plan_creates_subscription_when_none_exists() -> None:
    tenant = Tenant(name="Acme", subdomain=Subdomain("acme"))
    tenants = FakeTenantRepository()
    await tenants.add(tenant)
    plan = _plan()
    plans = FakeSubscriptionPlanRepository([plan])
    uow = FakePlatformUnitOfWork(
        tenants, FakeProductRepository(), FakeStoreSettingsRepository(), plans
    )

    subscription = await OverridePlanUseCase(uow).execute(
        OverridePlanInput(tenant_id=tenant.id, plan_id=plan.id)
    )

    assert subscription.plan_id == plan.id
    assert subscription.status == SubscriptionStatus.ACTIVE


async def test_override_plan_updates_existing_subscription() -> None:
    tenant = Tenant(name="Acme", subdomain=Subdomain("acme"))
    tenants = FakeTenantRepository()
    await tenants.add(tenant)
    old_plan = _plan(name="Starter")
    new_plan = _plan(name="Growth")
    plans = FakeSubscriptionPlanRepository([old_plan, new_plan])
    subscriptions = FakeTenantSubscriptionRepository()
    await subscriptions.upsert(TenantSubscription(tenant_id=tenant.id, plan_id=old_plan.id))
    uow = FakePlatformUnitOfWork(
        tenants, FakeProductRepository(), FakeStoreSettingsRepository(), plans, subscriptions
    )

    subscription = await OverridePlanUseCase(uow).execute(
        OverridePlanInput(tenant_id=tenant.id, plan_id=new_plan.id)
    )

    assert subscription.plan_id == new_plan.id
    stored = await subscriptions.get_by_tenant(tenant.id)
    assert stored is not None
    assert stored.plan_id == new_plan.id


async def test_override_plan_raises_for_unknown_plan() -> None:
    tenant = Tenant(name="Acme", subdomain=Subdomain("acme"))
    tenants = FakeTenantRepository()
    await tenants.add(tenant)
    uow = FakePlatformUnitOfWork(
        tenants,
        FakeProductRepository(),
        FakeStoreSettingsRepository(),
        FakeSubscriptionPlanRepository(),
    )

    with pytest.raises(EntityNotFoundError):
        await OverridePlanUseCase(uow).execute(
            OverridePlanInput(tenant_id=tenant.id, plan_id=uuid4())
        )
