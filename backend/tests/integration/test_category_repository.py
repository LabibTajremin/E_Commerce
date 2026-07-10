from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.category import Category
from src.domain.entities.tenant import Tenant
from src.domain.value_objects.slug import Slug
from src.domain.value_objects.subdomain import Subdomain
from src.infrastructure.db.repositories.sqlalchemy_category_repository import (
    SqlAlchemyCategoryRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)


async def _seed_tenant(session: AsyncSession, subdomain: str) -> Tenant:
    repo = SqlAlchemyTenantRepository(session)
    tenant = await repo.add(Tenant(name=subdomain, subdomain=Subdomain(subdomain)))
    await session.commit()
    return tenant


async def test_categories_are_isolated_per_tenant_with_same_slug(db_session: AsyncSession) -> None:
    tenant_a = await _seed_tenant(db_session, "cat-tenant-a")
    tenant_b = await _seed_tenant(db_session, "cat-tenant-b")
    repo = SqlAlchemyCategoryRepository(db_session)

    cat_a = await repo.add(Category(tenant_id=tenant_a.id, name="Sale", slug=Slug("sale")))
    cat_b = await repo.add(Category(tenant_id=tenant_b.id, name="Sale", slug=Slug("sale")))
    await db_session.commit()

    found_a = await repo.get_by_slug(tenant_a.id, "sale")
    found_b = await repo.get_by_slug(tenant_b.id, "sale")

    assert found_a is not None and found_a.id == cat_a.id
    assert found_b is not None and found_b.id == cat_b.id
    assert await repo.get_by_id(tenant_a.id, cat_b.id) is None


async def test_delete_category(db_session: AsyncSession) -> None:
    tenant = await _seed_tenant(db_session, "cat-tenant-c")
    repo = SqlAlchemyCategoryRepository(db_session)
    category = await repo.add(Category(tenant_id=tenant.id, name="Temp", slug=Slug("temp")))
    await db_session.commit()

    await repo.delete(tenant.id, category.id)
    await db_session.commit()

    assert await repo.get_by_id(tenant.id, category.id) is None
