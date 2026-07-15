from uuid import uuid4

import pytest

from src.application.use_cases.categories.create_category import (
    CreateCategoryInput,
    CreateCategoryUseCase,
)
from src.application.use_cases.categories.update_category import (
    DeleteCategoryUseCase,
    ListCategoriesUseCase,
    UpdateCategoryInput,
    UpdateCategoryUseCase,
)
from src.domain.exceptions import EntityNotFoundError, ValidationError
from tests.unit.application.fakes import FakeCategoryRepository


async def test_create_category_generates_slug_from_name() -> None:
    repo = FakeCategoryRepository()
    tenant_id = uuid4()

    category = await CreateCategoryUseCase(repo).execute(
        CreateCategoryInput(tenant_id=tenant_id, name="Summer Sale!")
    )

    assert str(category.slug) == "summer-sale"


async def test_create_category_deduplicates_slug_on_collision() -> None:
    repo = FakeCategoryRepository()
    tenant_id = uuid4()
    use_case = CreateCategoryUseCase(repo)
    await use_case.execute(CreateCategoryInput(tenant_id=tenant_id, name="Sale"))

    second = await use_case.execute(CreateCategoryInput(tenant_id=tenant_id, name="Sale"))

    assert str(second.slug) == "sale-2"


async def test_create_category_rejects_unknown_parent() -> None:
    repo = FakeCategoryRepository()
    with pytest.raises(EntityNotFoundError):
        await CreateCategoryUseCase(repo).execute(
            CreateCategoryInput(tenant_id=uuid4(), name="Sub", parent_id=uuid4())
        )


async def test_update_category_rejects_self_parenting() -> None:
    repo = FakeCategoryRepository()
    tenant_id = uuid4()
    category = await CreateCategoryUseCase(repo).execute(
        CreateCategoryInput(tenant_id=tenant_id, name="Root")
    )

    with pytest.raises(ValidationError):
        await UpdateCategoryUseCase(repo).execute(
            UpdateCategoryInput(tenant_id=tenant_id, category_id=category.id, parent_id=category.id)
        )


async def test_delete_and_list_categories() -> None:
    repo = FakeCategoryRepository()
    tenant_id = uuid4()
    use_case = CreateCategoryUseCase(repo)
    a = await use_case.execute(CreateCategoryInput(tenant_id=tenant_id, name="A"))
    await use_case.execute(CreateCategoryInput(tenant_id=tenant_id, name="B"))

    await DeleteCategoryUseCase(repo).execute(tenant_id, a.id)
    remaining = await ListCategoriesUseCase(repo).execute(tenant_id)

    assert len(remaining) == 1
    assert remaining[0].name == "B"
