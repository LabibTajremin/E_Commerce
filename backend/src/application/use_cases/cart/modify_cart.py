from dataclasses import dataclass
from uuid import UUID

from src.application.use_cases.cart.get_or_create_cart import CartIdentity, GetOrCreateCartUseCase
from src.domain.entities.cart import Cart
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.repositories.cart_repository import CartRepository
from src.domain.repositories.product_repository import ProductRepository


@dataclass(frozen=True, slots=True)
class AddCartItemInput:
    identity: CartIdentity
    product_id: UUID
    quantity: int


class AddCartItemUseCase:
    def __init__(
        self,
        cart_repository: CartRepository,
        product_repository: ProductRepository,
        get_or_create_cart: GetOrCreateCartUseCase,
    ) -> None:
        self._carts = cart_repository
        self._products = product_repository
        self._get_or_create_cart = get_or_create_cart

    async def execute(self, data: AddCartItemInput) -> Cart:
        product = await self._products.get_by_id(data.identity.tenant_id, data.product_id)
        if product is None:
            raise EntityNotFoundError("Product", data.product_id)
        if data.quantity <= 0:
            raise ValidationError("Quantity must be positive")

        cart = await self._get_or_create_cart.execute(data.identity)
        cart.add_item(data.product_id, data.quantity)
        return await self._carts.upsert(cart)


@dataclass(frozen=True, slots=True)
class UpdateCartItemInput:
    identity: CartIdentity
    product_id: UUID
    quantity: int


class UpdateCartItemUseCase:
    def __init__(
        self, cart_repository: CartRepository, get_or_create_cart: GetOrCreateCartUseCase
    ) -> None:
        self._carts = cart_repository
        self._get_or_create_cart = get_or_create_cart

    async def execute(self, data: UpdateCartItemInput) -> Cart:
        cart = await self._get_or_create_cart.execute(data.identity)
        cart.set_item_quantity(data.product_id, data.quantity)
        return await self._carts.upsert(cart)


@dataclass(frozen=True, slots=True)
class RemoveCartItemInput:
    identity: CartIdentity
    product_id: UUID


class RemoveCartItemUseCase:
    def __init__(
        self, cart_repository: CartRepository, get_or_create_cart: GetOrCreateCartUseCase
    ) -> None:
        self._carts = cart_repository
        self._get_or_create_cart = get_or_create_cart

    async def execute(self, data: RemoveCartItemInput) -> Cart:
        cart = await self._get_or_create_cart.execute(data.identity)
        cart.remove_item(data.product_id)
        return await self._carts.upsert(cart)
