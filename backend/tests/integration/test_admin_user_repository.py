from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.admin_user import AdminUser
from src.domain.entities.tenant import Tenant
from src.domain.value_objects.email import Email
from src.domain.value_objects.subdomain import Subdomain
from src.infrastructure.db.repositories.sqlalchemy_admin_user_repository import (
    SqlAlchemyAdminUserRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)


async def _seed_tenant(session: AsyncSession, subdomain: str) -> Tenant:
    tenant_repo = SqlAlchemyTenantRepository(session)
    tenant = await tenant_repo.add(Tenant(name=subdomain, subdomain=Subdomain(subdomain)))
    await session.commit()
    return tenant


async def test_add_and_get_admin_user_by_email(db_session: AsyncSession) -> None:
    tenant = await _seed_tenant(db_session, "au-tenant-a")
    repo = SqlAlchemyAdminUserRepository(db_session)
    user = AdminUser(
        tenant_id=tenant.id, email=Email("owner@a.com"), hashed_password="hashed"
    )

    await repo.add(user)
    await db_session.commit()

    found = await repo.get_by_email(tenant.id, "owner@a.com")
    assert found is not None
    assert found.id == user.id


async def test_admin_users_are_isolated_per_tenant(db_session: AsyncSession) -> None:
    tenant_a = await _seed_tenant(db_session, "au-tenant-b1")
    tenant_b = await _seed_tenant(db_session, "au-tenant-b2")
    repo = SqlAlchemyAdminUserRepository(db_session)

    await repo.add(
        AdminUser(tenant_id=tenant_a.id, email=Email("same@dup.com"), hashed_password="h1")
    )
    await repo.add(
        AdminUser(tenant_id=tenant_b.id, email=Email("same@dup.com"), hashed_password="h2")
    )
    await db_session.commit()

    found_in_a = await repo.get_by_email(tenant_a.id, "same@dup.com")
    found_in_b = await repo.get_by_email(tenant_b.id, "same@dup.com")

    assert found_in_a is not None and found_in_a.tenant_id == tenant_a.id
    assert found_in_b is not None and found_in_b.tenant_id == tenant_b.id
    assert found_in_a.id != found_in_b.id

    # Same email is allowed across tenants (uniqueness is per-tenant only).
    cross_lookup = await repo.get_by_id(tenant_a.id, found_in_b.id)
    assert cross_lookup is None
