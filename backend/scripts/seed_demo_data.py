"""Seed one demo tenant with an owner, two categories, and a handful of
published products — enough to exercise every MVP feature (branding,
catalog, cart, checkout, billing) immediately after a fresh deploy.

Run after migrations (`alembic upgrade head`), against whatever DATABASE_URL
is configured:

    python scripts/seed_demo_data.py --subdomain demo --owner-email owner@demo.example

Prompts for the owner's password (use --owner-password only for scripted/CI
use, since it leaks into shell history and the process list). Safe to
re-run: exits early if the subdomain is already taken.
"""

import argparse
import asyncio
import getpass
from decimal import Decimal
from uuid import UUID

from src.application.use_cases.auth.register_tenant_owner import (
    RegisterTenantOwnerInput,
    RegisterTenantOwnerUseCase,
)
from src.application.use_cases.billing.get_effective_plan import GetEffectivePlanUseCase
from src.application.use_cases.categories.create_category import (
    CreateCategoryInput,
    CreateCategoryUseCase,
)
from src.application.use_cases.products.bulk_update_status import (
    BulkUpdateStatusInput,
    BulkUpdateStatusUseCase,
)
from src.application.use_cases.products.create_product import (
    CreateProductInput,
    CreateProductUseCase,
)
from src.domain.entities.product import ProductStatus
from src.domain.exceptions import EntityAlreadyExistsError
from src.infrastructure.db.repositories.sqlalchemy_category_repository import (
    SqlAlchemyCategoryRepository,
)
from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

_CATEGORIES = ["Apparel", "Accessories"]

_PRODUCTS = [
    ("Classic Tee", "Apparel", Decimal("24.00"), 40),
    ("Everyday Hoodie", "Apparel", Decimal("58.00"), 25),
    ("Canvas Tote Bag", "Accessories", Decimal("18.00"), 60),
    ("Enamel Pin Set", "Accessories", Decimal("12.00"), 100),
    ("Weekender Cap", "Apparel", Decimal("22.00"), 35),
    ("Sticker Pack", "Accessories", Decimal("6.00"), 200),
]


async def seed(subdomain: str, tenant_name: str, owner_email: str, owner_password: str) -> None:
    register_uow = SqlAlchemyUnitOfWork()
    try:
        result = await RegisterTenantOwnerUseCase(register_uow).execute(
            RegisterTenantOwnerInput(
                tenant_name=tenant_name,
                subdomain=subdomain,
                owner_email=owner_email,
                owner_password=owner_password,
            )
        )
    except EntityAlreadyExistsError:
        print(f"Tenant subdomain {subdomain!r} already exists — skipping seed.")
        return

    tenant_id = result.tenant.id
    print(f"Created tenant {result.tenant.name!r} ({tenant_id}) at subdomain {subdomain!r}")
    print(f"Owner login: {owner_email}")

    catalog_uow = SqlAlchemyUnitOfWork(tenant_id=tenant_id)
    async with catalog_uow as uow:
        assert uow.session is not None
        category_repository = SqlAlchemyCategoryRepository(uow.session)

        category_ids: dict[str, UUID] = {}
        for name in _CATEGORIES:
            category = await CreateCategoryUseCase(category_repository).execute(
                CreateCategoryInput(tenant_id=tenant_id, name=name)
            )
            category_ids[name] = category.id

        get_effective_plan = GetEffectivePlanUseCase(
            uow.subscription_plans, uow.tenant_subscriptions
        )
        create_product = CreateProductUseCase(
            uow.products, category_repository, get_effective_plan
        )

        product_ids: list[UUID] = []
        for name, category_name, price, stock in _PRODUCTS:
            product = await create_product.execute(
                CreateProductInput(
                    tenant_id=tenant_id,
                    name=name,
                    price=price,
                    stock_qty=stock,
                    category_id=category_ids[category_name],
                )
            )
            product_ids.append(product.id)

        await BulkUpdateStatusUseCase(uow.products).execute(
            BulkUpdateStatusInput(
                tenant_id=tenant_id, product_ids=product_ids, status=ProductStatus.PUBLISHED
            )
        )
        await uow.commit()

    print(f"Seeded {len(_CATEGORIES)} categories and {len(_PRODUCTS)} published products.")
    print(f"Storefront:      https://{subdomain}.<your-storefront-domain>")
    print(f"Admin dashboard: https://{subdomain}.<your-admin-domain>/login")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--subdomain", default="demo")
    parser.add_argument("--tenant-name", default="Demo Store")
    parser.add_argument("--owner-email", default="owner@demo.example")
    parser.add_argument("--owner-password", default=None, help="Omit to be prompted securely.")
    args = parser.parse_args()

    password = args.owner_password or getpass.getpass("Owner password: ")
    asyncio.run(seed(args.subdomain, args.tenant_name, args.owner_email, password))
