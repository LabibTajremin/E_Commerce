from uuid import UUID

from pydantic import BaseModel, Field

from src.domain.entities.category import Category


class CategoryCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str | None = Field(default=None, max_length=255)
    parent_id: UUID | None = None


class CategoryUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    parent_id: UUID | None = None


class CategoryResponse(BaseModel):
    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    parent_id: UUID | None

    @classmethod
    def from_entity(cls, category: Category) -> "CategoryResponse":
        return cls(
            id=category.id,
            tenant_id=category.tenant_id,
            name=category.name,
            slug=str(category.slug),
            parent_id=category.parent_id,
        )
