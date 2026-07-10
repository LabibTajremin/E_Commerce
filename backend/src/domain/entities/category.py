from dataclasses import dataclass, field
from uuid import UUID, uuid4

from src.domain.value_objects.slug import Slug


@dataclass(slots=True)
class Category:
    tenant_id: UUID
    name: str
    slug: Slug
    id: UUID = field(default_factory=uuid4)
    parent_id: UUID | None = None
