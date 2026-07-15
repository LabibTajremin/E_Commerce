from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.use_cases.billing.get_effective_plan import GetEffectivePlanUseCase
from src.application.use_cases.categories.create_category import (
    CreateCategoryInput,
    CreateCategoryUseCase,
)
from src.application.use_cases.products.adjust_stock import AdjustStockInput, AdjustStockUseCase
from src.application.use_cases.products.bulk_update_status import (
    BulkUpdateStatusInput,
    BulkUpdateStatusUseCase,
)
from src.application.use_cases.products.create_product import (
    CreateProductInput,
    CreateProductUseCase,
)
from src.application.use_cases.products.list_products import (
    GetProductUseCase,
    ListProductsUseCase,
)
from src.application.use_cases.products.update_product import (
    UpdateProductInput,
    UpdateProductUseCase,
)
from src.application.use_cases.products.upload_product_image import (
    ReorderProductImagesInput,
    ReorderProductImagesUseCase,
    UploadProductImageInput,
    UploadProductImageUseCase,
)
from src.domain.entities.product import ProductStatus
from src.domain.entities.subscription_plan import SubscriptionPlan
from src.domain.exceptions import (
    EntityAlreadyExistsError,
    EntityNotFoundError,
    PlanLimitExceededError,
    ValidationError,
)
from src.domain.repositories.product_repository import ProductFilters
from src.domain.value_objects.money import Money
from tests.unit.application.fakes import (
    FakeCategoryRepository,
    FakeObjectStorage,
    FakeProductRepository,
    FakeSubscriptionPlanRepository,
    FakeTenantSubscriptionRepository,
    unlimited_plan_use_case,
)


async def test_create_product_generates_unique_slug() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    use_case = CreateProductUseCase(products, categories, unlimited_plan_use_case())

    first = await use_case.execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("9.99"))
    )
    second = await use_case.execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("9.99"))
    )

    assert str(first.slug) == "widget"
    assert str(second.slug) == "widget-2"


async def test_create_product_rejects_unknown_category() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()

    with pytest.raises(EntityNotFoundError):
        await CreateProductUseCase(products, categories, unlimited_plan_use_case()).execute(
            CreateProductInput(
                tenant_id=uuid4(), name="Widget", price=Decimal("9.99"), category_id=uuid4()
            )
        )


async def test_create_product_rejects_duplicate_sku_within_tenant() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    use_case = CreateProductUseCase(products, categories, unlimited_plan_use_case())
    await use_case.execute(
        CreateProductInput(tenant_id=tenant_id, name="A", price=Decimal("1"), sku="ABC-1")
    )

    with pytest.raises(EntityAlreadyExistsError):
        await use_case.execute(
            CreateProductInput(tenant_id=tenant_id, name="B", price=Decimal("2"), sku="abc-1")
        )


async def test_same_sku_allowed_across_different_tenants() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    use_case = CreateProductUseCase(products, categories, unlimited_plan_use_case())

    a = await use_case.execute(
        CreateProductInput(tenant_id=uuid4(), name="A", price=Decimal("1"), sku="SAME")
    )
    b = await use_case.execute(
        CreateProductInput(tenant_id=uuid4(), name="B", price=Decimal("2"), sku="SAME")
    )

    assert str(a.sku) == str(b.sku) == "SAME"


async def test_update_product_rejects_compare_at_price_below_price() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    product = await CreateProductUseCase(products, categories, unlimited_plan_use_case()).execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("10.00"))
    )

    with pytest.raises(ValidationError):
        await UpdateProductUseCase(products).execute(
            UpdateProductInput(
                tenant_id=tenant_id, product_id=product.id, compare_at_price=Decimal("5.00")
            )
        )


async def test_get_product_not_found_raises() -> None:
    with pytest.raises(EntityNotFoundError):
        await GetProductUseCase(FakeProductRepository()).execute(uuid4(), uuid4())


async def test_list_products_filters_by_status_and_paginates() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    create = CreateProductUseCase(products, categories, unlimited_plan_use_case())
    p1 = await create.execute(
        CreateProductInput(tenant_id=tenant_id, name="Published One", price=Decimal("1"))
    )
    p1.publish()
    await products.update(p1)
    await create.execute(
        CreateProductInput(tenant_id=tenant_id, name="Draft One", price=Decimal("2"))
    )

    page = await ListProductsUseCase(products).execute(
        tenant_id, ProductFilters(status=ProductStatus.PUBLISHED)
    )

    assert page.total == 1
    assert page.items[0].name == "Published One"


async def test_bulk_update_status() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    create = CreateProductUseCase(products, categories, unlimited_plan_use_case())
    p1 = await create.execute(CreateProductInput(tenant_id=tenant_id, name="A", price=Decimal("1")))
    p2 = await create.execute(CreateProductInput(tenant_id=tenant_id, name="B", price=Decimal("2")))

    updated = await BulkUpdateStatusUseCase(products).execute(
        BulkUpdateStatusInput(
            tenant_id=tenant_id, product_ids=[p1.id, p2.id], status=ProductStatus.PUBLISHED
        )
    )

    assert updated == 2
    refreshed = await products.get_by_id(tenant_id, p1.id)
    assert refreshed is not None
    assert refreshed.status == ProductStatus.PUBLISHED


async def test_adjust_stock_prevents_oversell() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    product = await CreateProductUseCase(products, categories, unlimited_plan_use_case()).execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("1"), stock_qty=2)
    )

    with pytest.raises(ValidationError):
        await AdjustStockUseCase(products).execute(
            AdjustStockInput(tenant_id=tenant_id, product_id=product.id, delta=-5)
        )


async def test_upload_and_reorder_product_images() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    storage = FakeObjectStorage()
    tenant_id = uuid4()
    product = await CreateProductUseCase(products, categories, unlimited_plan_use_case()).execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("1"))
    )

    upload_use_case = UploadProductImageUseCase(products, storage)
    updated = await upload_use_case.execute(
        UploadProductImageInput(
            tenant_id=tenant_id,
            product_id=product.id,
            content=b"fake",
            content_type="image/png",
            filename="a.png",
        )
    )
    updated = await upload_use_case.execute(
        UploadProductImageInput(
            tenant_id=tenant_id,
            product_id=product.id,
            content=b"fake2",
            content_type="image/png",
            filename="b.png",
        )
    )
    assert len(updated.images) == 2

    reversed_urls = list(reversed(updated.images))
    reordered = await ReorderProductImagesUseCase(products).execute(
        ReorderProductImagesInput(
            tenant_id=tenant_id, product_id=product.id, ordered_urls=reversed_urls
        )
    )
    assert reordered.images == reversed_urls


async def test_create_product_with_valid_category_succeeds() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    category = await CreateCategoryUseCase(categories).execute(
        CreateCategoryInput(tenant_id=tenant_id, name="Gadgets")
    )

    product = await CreateProductUseCase(products, categories, unlimited_plan_use_case()).execute(
        CreateProductInput(
            tenant_id=tenant_id, name="Widget", price=Decimal("1"), category_id=category.id
        )
    )

    assert product.category_id == category.id


async def test_create_product_rejects_when_plan_product_limit_reached() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    plan = SubscriptionPlan(
        name="Starter",
        price=Money(Decimal("0")),
        max_products=1,
        max_banners=1,
        custom_domain_allowed=False,
    )
    get_effective_plan = GetEffectivePlanUseCase(
        FakeSubscriptionPlanRepository([plan]), FakeTenantSubscriptionRepository()
    )
    use_case = CreateProductUseCase(products, categories, get_effective_plan)

    await use_case.execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget One", price=Decimal("1"))
    )

    with pytest.raises(PlanLimitExceededError):
        await use_case.execute(
            CreateProductInput(tenant_id=tenant_id, name="Widget Two", price=Decimal("1"))
        )
