from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.use_cases.categories.create_category import (
    CreateCategoryInput,
    CreateCategoryUseCase,
)
from src.application.use_cases.products.create_product import (
    CreateProductInput,
    CreateProductUseCase,
)
from src.application.use_cases.storefront.get_public_product import (
    GetPublicProductBySlugUseCase,
)
from src.application.use_cases.storefront.list_public_categories import (
    ListPublicCategoriesUseCase,
)
from src.application.use_cases.storefront.list_public_products import (
    ListPublicProductsUseCase,
    PublicProductFilters,
)
from src.domain.exceptions import EntityNotFoundError
from tests.unit.application.fakes import FakeCategoryRepository, FakeProductRepository


async def test_list_public_products_only_returns_published() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    create = CreateProductUseCase(products, categories)
    draft = await create.execute(
        CreateProductInput(tenant_id=tenant_id, name="Draft", price=Decimal("1"))
    )
    published = await create.execute(
        CreateProductInput(tenant_id=tenant_id, name="Published", price=Decimal("2"))
    )
    published.publish()
    await products.update(published)

    page = await ListPublicProductsUseCase(products).execute(tenant_id, PublicProductFilters())

    assert page.total == 1
    assert page.items[0].id == published.id
    assert draft.id not in {p.id for p in page.items}


async def test_get_public_product_404s_for_draft() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    draft = await CreateProductUseCase(products, categories).execute(
        CreateProductInput(tenant_id=tenant_id, name="Draft", price=Decimal("1"))
    )

    with pytest.raises(EntityNotFoundError):
        await GetPublicProductBySlugUseCase(products).execute(tenant_id, str(draft.slug))


async def test_get_public_product_404s_for_nonexistent_slug() -> None:
    with pytest.raises(EntityNotFoundError):
        await GetPublicProductBySlugUseCase(FakeProductRepository()).execute(uuid4(), "ghost")


async def test_get_public_product_returns_published() -> None:
    products = FakeProductRepository()
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    product = await CreateProductUseCase(products, categories).execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("1"))
    )
    product.publish()
    await products.update(product)

    found = await GetPublicProductBySlugUseCase(products).execute(tenant_id, str(product.slug))

    assert found.id == product.id


async def test_list_public_categories() -> None:
    categories = FakeCategoryRepository()
    tenant_id = uuid4()
    await CreateCategoryUseCase(categories).execute(
        CreateCategoryInput(tenant_id=tenant_id, name="Gadgets")
    )

    result = await ListPublicCategoriesUseCase(categories).execute(tenant_id)

    assert len(result) == 1
    assert result[0].name == "Gadgets"
