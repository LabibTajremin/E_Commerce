from uuid import UUID

from fastapi import APIRouter

from src.application.use_cases.cart.get_or_create_cart import GetOrCreateCartUseCase
from src.application.use_cases.cart.modify_cart import (
    AddCartItemInput,
    AddCartItemUseCase,
    RemoveCartItemInput,
    RemoveCartItemUseCase,
    UpdateCartItemInput,
    UpdateCartItemUseCase,
)
from src.presentation.dependencies import CartIdentityDep, CartRepositoryDep, ProductRepositoryDep
from src.presentation.schemas.cart import AddCartItemRequest, CartResponse, UpdateCartItemRequest

router = APIRouter(prefix="/cart", tags=["storefront:cart"])


@router.get("", response_model=CartResponse)
async def get_cart(identity: CartIdentityDep, cart_repository: CartRepositoryDep) -> CartResponse:
    use_case = GetOrCreateCartUseCase(cart_repository)
    cart = await use_case.execute(identity)
    return CartResponse.from_entity(cart)


@router.post("/items", response_model=CartResponse)
async def add_cart_item(
    body: AddCartItemRequest,
    identity: CartIdentityDep,
    cart_repository: CartRepositoryDep,
    product_repository: ProductRepositoryDep,
) -> CartResponse:
    get_or_create = GetOrCreateCartUseCase(cart_repository)
    use_case = AddCartItemUseCase(cart_repository, product_repository, get_or_create)
    cart = await use_case.execute(
        AddCartItemInput(identity=identity, product_id=body.product_id, quantity=body.quantity)
    )
    return CartResponse.from_entity(cart)


@router.put("/items/{product_id}", response_model=CartResponse)
async def update_cart_item(
    product_id: UUID,
    body: UpdateCartItemRequest,
    identity: CartIdentityDep,
    cart_repository: CartRepositoryDep,
) -> CartResponse:
    get_or_create = GetOrCreateCartUseCase(cart_repository)
    use_case = UpdateCartItemUseCase(cart_repository, get_or_create)
    cart = await use_case.execute(
        UpdateCartItemInput(identity=identity, product_id=product_id, quantity=body.quantity)
    )
    return CartResponse.from_entity(cart)


@router.delete("/items/{product_id}", response_model=CartResponse)
async def remove_cart_item(
    product_id: UUID, identity: CartIdentityDep, cart_repository: CartRepositoryDep
) -> CartResponse:
    get_or_create = GetOrCreateCartUseCase(cart_repository)
    use_case = RemoveCartItemUseCase(cart_repository, get_or_create)
    cart = await use_case.execute(RemoveCartItemInput(identity=identity, product_id=product_id))
    return CartResponse.from_entity(cart)
