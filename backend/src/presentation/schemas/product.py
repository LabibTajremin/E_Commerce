from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities.product import Product, ProductStatus


class ProductCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    price: Decimal = Field(ge=0)
    slug: str | None = Field(default=None, max_length=255)
    description: str | None = None
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=50)
    stock_qty: int = Field(default=0, ge=0)
    category_id: UUID | None = None


class ProductUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    price: Decimal | None = Field(default=None, ge=0)
    compare_at_price: Decimal | None = Field(default=None, ge=0)
    sku: str | None = Field(default=None, max_length=50)
    category_id: UUID | None = None


class BulkStatusUpdateRequest(BaseModel):
    product_ids: list[UUID] = Field(min_length=1)
    status: ProductStatus


class StockAdjustmentRequest(BaseModel):
    delta: int


class ReorderImagesRequest(BaseModel):
    ordered_urls: list[str]


class ProductResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    description: str | None
    price: Decimal
    compare_at_price: Decimal | None
    sku: str | None
    images: list[str]
    stock_qty: int
    status: ProductStatus
    category_id: UUID | None

    @classmethod
    def from_entity(cls, product: Product) -> "ProductResponse":
        return cls(
            id=product.id,
            tenant_id=product.tenant_id,
            name=product.name,
            slug=str(product.slug),
            description=product.description,
            price=product.price.amount,
            compare_at_price=product.compare_at_price.amount if product.compare_at_price else None,
            sku=str(product.sku) if product.sku else None,
            images=product.images,
            stock_qty=product.stock_qty,
            status=product.status,
            category_id=product.category_id,
        )


class ProductPageResponse(BaseModel):
    items: list[ProductResponse]
    total: int
