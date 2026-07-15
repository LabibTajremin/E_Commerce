import asyncio
from decimal import Decimal
from uuid import UUID

from src.application.use_cases.orders.checkout import CheckoutInput, CheckoutUseCase
from src.core.security import hash_password
from src.domain.entities.cart import Cart
from src.domain.entities.customer import Customer
from src.domain.entities.product import Product
from src.domain.entities.tenant import Tenant
from src.domain.exceptions import OutOfStockError
from src.domain.value_objects.address import Address
from src.domain.value_objects.email import Email
from src.domain.value_objects.money import Money
from src.domain.value_objects.slug import Slug
from src.domain.value_objects.subdomain import Subdomain
from src.infrastructure.db.repositories.sqlalchemy_cart_repository import SqlAlchemyCartRepository
from src.infrastructure.db.repositories.sqlalchemy_customer_repository import (
    SqlAlchemyCustomerRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_product_repository import (
    SqlAlchemyProductRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)

_ADDRESS = Address(
    line1="1 Main St", city="Metropolis", state="CA", postal_code="90210", country="US"
)


async def test_two_concurrent_checkouts_on_last_unit_never_oversell(
    database_url: str, _run_migrations: None
) -> None:
    """DoD: race-condition test simulating two simultaneous checkouts on the
    last unit in stock, proving no oversell. Looped 5x in one test run for
    reliability, on top of CI re-running the suite on every push."""
    # SqlAlchemyUnitOfWork binds `async_session_factory` via a name import, so
    # the source module's attribute must be reassigned *and* the already-bound
    # name in the consuming module patched too — the standard "patch where a
    # name is used, not where it's defined" issue with `from x import y`.
    import src.infrastructure.db.session as session_module
    import src.infrastructure.db.unit_of_work as uow_module

    session_module.engine = session_module.create_engine(database_url)
    session_module.async_session_factory = session_module.async_sessionmaker(
        session_module.engine, expire_on_commit=False, autoflush=False
    )
    uow_module.async_session_factory = session_module.async_session_factory

    from src.infrastructure.db.unit_of_work import SqlAlchemyUnitOfWork

    session_factory = session_module.async_session_factory

    for iteration in range(5):
        async with session_factory() as seed_session:
            tag = f"race{iteration}"
            tenant = await SqlAlchemyTenantRepository(seed_session).add(
                Tenant(name=tag, subdomain=Subdomain(tag))
            )
            product = await SqlAlchemyProductRepository(seed_session).add(
                Product(
                    tenant_id=tenant.id,
                    name="Last Unit Widget",
                    slug=Slug(f"{tag}-widget"),
                    price=Money(Decimal("20.00")),
                    stock_qty=1,
                )
            )
            customer_a = await SqlAlchemyCustomerRepository(seed_session).add(
                Customer(
                    tenant_id=tenant.id,
                    email=Email(f"a@{tag}.com"),
                    hashed_password=hash_password("x"),
                    name="Buyer A",
                )
            )
            customer_b = await SqlAlchemyCustomerRepository(seed_session).add(
                Customer(
                    tenant_id=tenant.id,
                    email=Email(f"b@{tag}.com"),
                    hashed_password=hash_password("x"),
                    name="Buyer B",
                )
            )
            cart_repo = SqlAlchemyCartRepository(seed_session)
            cart_a = Cart(tenant_id=tenant.id, customer_id=customer_a.id)
            cart_a.add_item(product.id, 1)
            await cart_repo.upsert(cart_a)
            cart_b = Cart(tenant_id=tenant.id, customer_id=customer_b.id)
            cart_b.add_item(product.id, 1)
            await cart_repo.upsert(cart_b)
            await seed_session.commit()

        async def checkout_for(
            customer_id: UUID, tenant_id: UUID = tenant.id
        ) -> tuple[str, object]:
            uow = SqlAlchemyUnitOfWork(tenant_id=tenant_id)
            try:
                order = await CheckoutUseCase(uow).execute(
                    CheckoutInput(
                        tenant_id=tenant_id, customer_id=customer_id, shipping_address=_ADDRESS
                    )
                )
                return ("ok", order)
            except OutOfStockError as exc:
                return ("out_of_stock", exc)

        results = await asyncio.gather(checkout_for(customer_a.id), checkout_for(customer_b.id))

        outcomes = [r[0] for r in results]
        assert outcomes.count("ok") == 1, (
            f"iteration {iteration}: expected exactly 1 success, got {outcomes}"
        )
        assert outcomes.count("out_of_stock") == 1, (
            f"iteration {iteration}: expected exactly 1 rejection, got {outcomes}"
        )

        async with session_factory() as check_session:
            refreshed = await SqlAlchemyProductRepository(check_session).get_by_id(
                tenant.id, product.id
            )
            assert refreshed is not None
            assert refreshed.stock_qty == 0, (
                f"iteration {iteration}: stock_qty should be exactly 0 after one "
                f"successful sale of the last unit, got {refreshed.stock_qty}"
            )
