from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.product import Product, ProductStatus
from src.domain.entities.tenant import Tenant
from src.domain.repositories.product_repository import ProductFilters
from src.domain.value_objects.money import Money
from src.domain.value_objects.slug import Slug
from src.domain.value_objects.subdomain import Subdomain
from src.infrastructure.db.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)


async def _seed_tenant(session: AsyncSession, subdomain: str) -> Tenant:
    repo = SqlAlchemyTenantRepository(session)
    tenant = await repo.add(Tenant(name=subdomain, subdomain=Subdomain(subdomain)))
    await session.commit()
    return tenant


async def test_add_get_by_id_and_slug(db_session: AsyncSession) -> None:
    tenant = await _seed_tenant(db_session, "pr-tenant-a")
    repo = SqlAlchemyProductRepository(db_session)
    product = Product(
        tenant_id=tenant.id, name="Widget", slug=Slug("widget"), price=Money(Decimal("9.99"))
    )

    await repo.add(product)
    await db_session.commit()

    by_id = await repo.get_by_id(tenant.id, product.id)
    by_slug = await repo.get_by_slug(tenant.id, "widget")
    assert by_id is not None and by_id.id == product.id
    assert by_slug is not None and by_slug.id == product.id


async def test_list_filters_by_status_category_and_price(db_session: AsyncSession) -> None:
    tenant = await _seed_tenant(db_session, "pr-tenant-b")
    repo = SqlAlchemyProductRepository(db_session)

    cheap_draft = Product(
        tenant_id=tenant.id, name="Cheap Draft", slug=Slug("cheap-draft"), price=Money(Decimal("5"))
    )
    expensive_published = Product(
        tenant_id=tenant.id,
        name="Expensive Published",
        slug=Slug("expensive-published"),
        price=Money(Decimal("500")),
        status=ProductStatus.PUBLISHED,
    )
    await repo.add(cheap_draft)
    await repo.add(expensive_published)
    await db_session.commit()

    published_only = await repo.list(tenant.id, ProductFilters(status=ProductStatus.PUBLISHED))
    assert {p.id for p in published_only} == {expensive_published.id}

    under_100 = await repo.list(tenant.id, ProductFilters(max_price=Decimal("100")))
    assert {p.id for p in under_100} == {cheap_draft.id}


async def test_full_text_search_matches_name_and_description(db_session: AsyncSession) -> None:
    tenant = await _seed_tenant(db_session, "pr-tenant-c")
    repo = SqlAlchemyProductRepository(db_session)

    match = Product(
        tenant_id=tenant.id,
        name="Wireless Mechanical Keyboard",
        slug=Slug("keyboard"),
        description="A premium keyboard for developers",
        price=Money(Decimal("120")),
    )
    no_match = Product(
        tenant_id=tenant.id, name="Coffee Mug", slug=Slug("mug"), price=Money(Decimal("12"))
    )
    await repo.add(match)
    await repo.add(no_match)
    await db_session.commit()

    results = await repo.list(tenant.id, ProductFilters(search="keyboard"))
    assert {p.id for p in results} == {match.id}


async def test_pagination_limit_and_offset(db_session: AsyncSession) -> None:
    tenant = await _seed_tenant(db_session, "pr-tenant-d")
    repo = SqlAlchemyProductRepository(db_session)
    for i in range(5):
        await repo.add(
            Product(
                tenant_id=tenant.id,
                name=f"Product {i}",
                slug=Slug(f"product-{i}"),
                price=Money(Decimal("1")),
            )
        )
    await db_session.commit()

    total = await repo.count(tenant.id, ProductFilters())
    page_1 = await repo.list(tenant.id, ProductFilters(limit=2, offset=0))
    page_2 = await repo.list(tenant.id, ProductFilters(limit=2, offset=2))

    assert total == 5
    assert len(page_1) == 2
    assert len(page_2) == 2
    assert {p.id for p in page_1}.isdisjoint({p.id for p in page_2})


async def test_three_tenants_with_overlapping_names_and_slugs_never_leak(
    db_session: AsyncSession,
) -> None:
    """DoD: seed 3 tenants with overlapping product names/slugs and confirm
    zero cross-tenant leakage in list/search/get."""
    tenants = [await _seed_tenant(db_session, f"pr-leak-{i}") for i in range(3)]
    repo = SqlAlchemyProductRepository(db_session)

    products_by_tenant = {}
    for tenant in tenants:
        product = Product(
            tenant_id=tenant.id,
            name="Overlapping Product Name",
            slug=Slug("overlapping-slug"),
            description="shared search term across tenants",
            price=Money(Decimal("42.00")),
        )
        await repo.add(product)
        products_by_tenant[tenant.id] = product
    await db_session.commit()

    for tenant in tenants:
        by_slug = await repo.get_by_slug(tenant.id, "overlapping-slug")
        assert by_slug is not None
        assert by_slug.id == products_by_tenant[tenant.id].id

        listed = await repo.list(tenant.id, ProductFilters())
        assert {p.id for p in listed} == {products_by_tenant[tenant.id].id}

        searched = await repo.list(tenant.id, ProductFilters(search="shared search term"))
        assert {p.id for p in searched} == {products_by_tenant[tenant.id].id}

        other_tenants_products = {
            p.id for tid, p in products_by_tenant.items() if tid != tenant.id
        }
        for other_id in other_tenants_products:
            assert await repo.get_by_id(tenant.id, other_id) is None
