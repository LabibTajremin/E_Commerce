from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from src.application.use_cases.cart.get_or_create_cart import CartIdentity, GetOrCreateCartUseCase
from src.application.use_cases.cart.modify_cart import (
    AddCartItemInput,
    AddCartItemUseCase,
    RemoveCartItemInput,
    RemoveCartItemUseCase,
    UpdateCartItemInput,
    UpdateCartItemUseCase,
)
from src.application.use_cases.products.create_product import (
    CreateProductInput,
    CreateProductUseCase,
)
from src.domain.entities.product import Product
from src.domain.exceptions import EntityNotFoundError
from tests.unit.application.fakes import (
    FakeCartRepository,
    FakeCategoryRepository,
    FakeProductRepository,
    unlimited_plan_use_case,
)


async def _make_product(products: FakeProductRepository, tenant_id: UUID) -> Product:
    categories = FakeCategoryRepository()
    return await CreateProductUseCase(products, categories, unlimited_plan_use_case()).execute(
        CreateProductInput(tenant_id=tenant_id, name="Widget", price=Decimal("9.99"))
    )


async def test_get_or_create_cart_is_idempotent_for_session() -> None:
    carts = FakeCartRepository()
    tenant_id = uuid4()
    identity = CartIdentity(tenant_id=tenant_id, session_id="sess-1")
    use_case = GetOrCreateCartUseCase(carts)

    first = await use_case.execute(identity)
    second = await use_case.execute(identity)

    assert first.id == second.id


async def test_add_cart_item_requires_existing_product() -> None:
    carts = FakeCartRepository()
    products = FakeProductRepository()
    get_or_create = GetOrCreateCartUseCase(carts)

    with pytest.raises(EntityNotFoundError):
        await AddCartItemUseCase(carts, products, get_or_create).execute(
            AddCartItemInput(
                identity=CartIdentity(tenant_id=uuid4(), session_id="s1"),
                product_id=uuid4(),
                quantity=1,
            )
        )


async def test_add_update_remove_cart_item_flow() -> None:
    carts = FakeCartRepository()
    products = FakeProductRepository()
    tenant_id = uuid4()
    product = await _make_product(products, tenant_id)
    identity = CartIdentity(tenant_id=tenant_id, session_id="s1")
    get_or_create = GetOrCreateCartUseCase(carts)

    cart = await AddCartItemUseCase(carts, products, get_or_create).execute(
        AddCartItemInput(identity=identity, product_id=product.id, quantity=2)
    )
    assert cart.line_items[0].quantity == 2

    cart = await UpdateCartItemUseCase(carts, get_or_create).execute(
        UpdateCartItemInput(identity=identity, product_id=product.id, quantity=5)
    )
    assert cart.line_items[0].quantity == 5

    cart = await RemoveCartItemUseCase(carts, get_or_create).execute(
        RemoveCartItemInput(identity=identity, product_id=product.id)
    )
    assert cart.line_items == []
