from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

from src.application.use_cases._slug import generate_unique_slug
from src.application.use_cases.billing.get_effective_plan import GetEffectivePlanUseCase
from src.domain.entities.product import Product
from src.domain.exceptions import EntityAlreadyExistsError, EntityNotFoundError
from src.domain.repositories.category_repository import CategoryRepository
from src.domain.repositories.product_repository import ProductFilters, ProductRepository
from src.domain.services.plan_limit_policy import PlanLimitPolicy
from src.domain.value_objects.money import Money
from src.domain.value_objects.sku import SKU


@dataclass(frozen=True, slots=True)
class CreateProductInput:
    tenant_id: UUID
    name: str
    price: Decimal
    slug: str | None = None
    description: str | None = None
    compare_at_price: Decimal | None = None
    sku: str | None = None
    stock_qty: int = 0
    category_id: UUID | None = None


class CreateProductUseCase:
    def __init__(
        self,
        product_repository: ProductRepository,
        category_repository: CategoryRepository,
        get_effective_plan: GetEffectivePlanUseCase,
    ) -> None:
        self._products = product_repository
        self._categories = category_repository
        self._get_effective_plan = get_effective_plan

    async def execute(self, data: CreateProductInput) -> Product:
        if data.category_id is not None:
            category = await self._categories.get_by_id(data.tenant_id, data.category_id)
            if category is None:
                raise EntityNotFoundError("Category", data.category_id)

        plan = await self._get_effective_plan.execute(data.tenant_id)
        current_count = await self._products.count(data.tenant_id, ProductFilters())
        PlanLimitPolicy.check_product_limit(current_count, plan)

        sku = SKU(data.sku) if data.sku else None
        if sku is not None and await self._products.get_by_sku(data.tenant_id, str(sku)):
            raise EntityAlreadyExistsError("Product SKU", str(sku))

        async def slug_exists(slug: str) -> bool:
            return await self._products.get_by_slug(data.tenant_id, slug) is not None

        slug = await generate_unique_slug(data.slug or data.name, slug_exists)

        product = Product(
            tenant_id=data.tenant_id,
            name=data.name,
            slug=slug,
            description=data.description,
            price=Money(data.price),
            compare_at_price=Money(data.compare_at_price) if data.compare_at_price else None,
            sku=sku,
            stock_qty=data.stock_qty,
            category_id=data.category_id,
        )
        return await self._products.add(product)
