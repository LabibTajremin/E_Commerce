import uuid
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from src.application.interfaces.storage import ObjectStorage
from src.application.use_cases.billing.get_effective_plan import GetEffectivePlanUseCase
from src.application.use_cases.themes.get_store_settings import GetStoreSettingsUseCase
from src.domain.entities.store_settings import StoreSettings
from src.domain.exceptions import ValidationError
from src.domain.repositories.store_settings_repository import StoreSettingsRepository
from src.domain.services.plan_limit_policy import PlanLimitPolicy

MAX_IMAGE_SIZE_BYTES = 5 * 1024 * 1024
ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/webp"}


class ImageKind(StrEnum):
    LOGO = "logo"
    FAVICON = "favicon"
    BANNER = "banner"


@dataclass(frozen=True, slots=True)
class UploadStoreImageInput:
    tenant_id: UUID
    kind: ImageKind
    content: bytes
    content_type: str
    filename: str


class UploadStoreImageUseCase:
    def __init__(
        self,
        store_settings_repository: StoreSettingsRepository,
        get_store_settings: GetStoreSettingsUseCase,
        object_storage: ObjectStorage,
        get_effective_plan: GetEffectivePlanUseCase,
    ) -> None:
        self._store_settings = store_settings_repository
        self._get_store_settings = get_store_settings
        self._storage = object_storage
        self._get_effective_plan = get_effective_plan

    async def execute(self, data: UploadStoreImageInput) -> StoreSettings:
        if data.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError(
                f"Unsupported image type {data.content_type!r}; "
                f"allowed: {sorted(ALLOWED_CONTENT_TYPES)}"
            )
        if len(data.content) > MAX_IMAGE_SIZE_BYTES:
            raise ValidationError(
                f"Image exceeds max size of {MAX_IMAGE_SIZE_BYTES // (1024 * 1024)}MB"
            )

        extension = data.filename.rsplit(".", 1)[-1].lower() if "." in data.filename else "bin"
        key = f"tenants/{data.tenant_id}/{data.kind.value}/{uuid.uuid4()}.{extension}"
        url = await self._storage.upload(
            key=key, content=data.content, content_type=data.content_type
        )

        settings = await self._get_store_settings.execute(data.tenant_id)
        if data.kind == ImageKind.LOGO:
            settings.logo_url = url
        elif data.kind == ImageKind.FAVICON:
            settings.favicon_url = url
        else:
            plan = await self._get_effective_plan.execute(data.tenant_id)
            PlanLimitPolicy.check_banner_limit(len(settings.banner_images), plan)
            settings.add_banner(url)

        return await self._store_settings.upsert(settings)
