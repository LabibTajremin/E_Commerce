from collections.abc import Awaitable, Callable

from src.domain.value_objects.slug import Slug


async def generate_unique_slug(base_text: str, exists: Callable[[str], Awaitable[bool]]) -> Slug:
    """Generates a slug from `base_text`, appending `-2`, `-3`, ... on collision."""
    candidate = Slug.from_text(base_text)
    suffix = 1
    while await exists(str(candidate)):
        suffix += 1
        candidate = Slug(f"{Slug.from_text(base_text)}-{suffix}")
    return candidate
