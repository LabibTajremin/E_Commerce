from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from src.domain.exceptions import ValidationError
from src.domain.value_objects.money import Money
from src.domain.value_objects.sku import SKU
from src.domain.value_objects.slug import Slug


class ProductStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


@dataclass(slots=True)
class Product:
    tenant_id: UUID
    name: str
    slug: Slug
    price: Money
    id: UUID = field(default_factory=uuid4)
    description: str | None = None
    compare_at_price: Money | None = None
    sku: SKU | None = None
    images: list[str] = field(default_factory=list)
    stock_qty: int = 0
    status: ProductStatus = ProductStatus.DRAFT
    category_id: UUID | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    def __post_init__(self) -> None:
        if self.stock_qty < 0:
            raise ValidationError("stock_qty cannot be negative")
        if (
            self.compare_at_price is not None
            and self.compare_at_price.amount < self.price.amount
        ):
            raise ValidationError("compare_at_price cannot be less than price")

    def publish(self) -> None:
        self.status = ProductStatus.PUBLISHED

    def unpublish(self) -> None:
        self.status = ProductStatus.DRAFT

    def adjust_stock(self, delta: int) -> None:
        new_qty = self.stock_qty + delta
        if new_qty < 0:
            raise ValidationError(
                f"Cannot adjust stock by {delta}: would go negative from {self.stock_qty}"
            )
        self.stock_qty = new_qty

    def reorder_images(self, ordered_urls: list[str]) -> None:
        if set(ordered_urls) != set(self.images):
            raise ValidationError("reorder_images must contain exactly the existing image set")
        self.images = ordered_urls
