import uuid
from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.storage import ObjectStorage
from src.domain.entities.product import Product
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.repositories.product_repository import ProductRepository

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}
MAX_IMAGES_PER_PRODUCT = 10


@dataclass(frozen=True, slots=True)
class UploadProductImageInput:
    tenant_id: UUID
    product_id: UUID
    content: bytes
    content_type: str
    filename: str


class UploadProductImageUseCase:
    def __init__(
        self, product_repository: ProductRepository, object_storage: ObjectStorage
    ) -> None:
        self._products = product_repository
        self._storage = object_storage

    async def execute(self, data: UploadProductImageInput) -> Product:
        product = await self._products.get_by_id(data.tenant_id, data.product_id)
        if product is None:
            raise EntityNotFoundError("Product", data.product_id)

        if data.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError(
                f"Unsupported image type {data.content_type!r}; "
                f"allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
            )
        if len(data.content) > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError(
                f"Image exceeds max size of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB"
            )
        if len(product.images) >= MAX_IMAGES_PER_PRODUCT:
            raise ValidationError(f"Product already has the max of {MAX_IMAGES_PER_PRODUCT} images")

        extension = data.filename.rsplit(".", 1)[-1].lower() if "." in data.filename else "bin"
        key = f"tenants/{data.tenant_id}/products/{data.product_id}/{uuid.uuid4()}.{extension}"
        url = await self._storage.upload(
            key=key, content=data.content, content_type=data.content_type
        )
        product.images.append(url)
        return await self._products.update(product)


@dataclass(frozen=True, slots=True)
class ReorderProductImagesInput:
    tenant_id: UUID
    product_id: UUID
    ordered_urls: list[str]


class ReorderProductImagesUseCase:
    def __init__(self, product_repository: ProductRepository) -> None:
        self._products = product_repository

    async def execute(self, data: ReorderProductImagesInput) -> Product:
        product = await self._products.get_by_id(data.tenant_id, data.product_id)
        if product is None:
            raise EntityNotFoundError("Product", data.product_id)
        product.reorder_images(data.ordered_urls)
        return await self._products.update(product)
