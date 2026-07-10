from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from src.domain.entities.category import Category
from src.domain.entities.product import Product
from src.domain.entities.store_settings import StoreSettings


class PublicProductResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    description: str | None
    price: Decimal
    compare_at_price: Decimal | None
    images: list[str]
    category_id: UUID | None
    in_stock: bool

    @classmethod
    def from_entity(cls, product: Product) -> "PublicProductResponse":
        return cls(
            id=product.id,
            name=product.name,
            slug=str(product.slug),
            description=product.description,
            price=product.price.amount,
            compare_at_price=product.compare_at_price.amount if product.compare_at_price else None,
            images=product.images,
            category_id=product.category_id,
            in_stock=product.stock_qty > 0,
        )


class PublicProductPageResponse(BaseModel):
    items: list[PublicProductResponse]
    total: int


class PublicCategoryResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    parent_id: UUID | None

    @classmethod
    def from_entity(cls, category: Category) -> "PublicCategoryResponse":
        return cls(
            id=category.id,
            name=category.name,
            slug=str(category.slug),
            parent_id=category.parent_id,
        )


class PublicCategoryListResponse(BaseModel):
    items: list[PublicCategoryResponse]


class PublicStoreSettingsResponse(BaseModel):
    store_name: str
    logo_url: str | None
    favicon_url: str | None
    primary_color: str
    accent_color: str
    font_choice: str
    banner_images: list[str]
    announcement_bar_text: str | None
    social_links: dict[str, str]
    enabled_sections: dict[str, bool]

    @classmethod
    def from_entity(cls, settings: StoreSettings) -> "PublicStoreSettingsResponse":
        return cls(
            store_name=settings.store_name,
            logo_url=settings.logo_url,
            favicon_url=settings.favicon_url,
            primary_color=str(settings.primary_color),
            accent_color=str(settings.accent_color),
            font_choice=settings.font_choice,
            banner_images=settings.banner_images,
            announcement_bar_text=settings.announcement_bar_text,
            social_links=settings.social_links,
            enabled_sections=settings.enabled_sections,
        )
