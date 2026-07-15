from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.store_settings import StoreSettings
from src.domain.entities.tenant import Tenant
from src.domain.value_objects.subdomain import Subdomain
from src.infrastructure.db.repositories.sqlalchemy_store_settings_repository import (
    SqlAlchemyStoreSettingsRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_tenant_repository import (
    SqlAlchemyTenantRepository,
)
from src.infrastructure.db.repositories.sqlalchemy_theme_repository import (
    SqlAlchemyThemeRepository,
)


async def _seed_tenant(session: AsyncSession, subdomain: str) -> Tenant:
    repo = SqlAlchemyTenantRepository(session)
    tenant = await repo.add(Tenant(name=subdomain, subdomain=Subdomain(subdomain)))
    await session.commit()
    return tenant


async def test_upsert_creates_then_updates_settings(db_session: AsyncSession) -> None:
    tenant = await _seed_tenant(db_session, "ss-tenant-a")
    theme = (await SqlAlchemyThemeRepository(db_session).list())[0]
    repo = SqlAlchemyStoreSettingsRepository(db_session)

    created = await repo.upsert(StoreSettings(tenant_id=tenant.id, theme_id=theme.id))
    await db_session.commit()
    assert created.store_name == ""

    created.store_name = "Acme"
    updated = await repo.upsert(created)
    await db_session.commit()

    assert updated.id == created.id
    assert updated.store_name == "Acme"

    fetched = await repo.get_by_tenant(tenant.id)
    assert fetched is not None
    assert fetched.store_name == "Acme"


async def test_settings_are_isolated_per_tenant(db_session: AsyncSession) -> None:
    tenant_a = await _seed_tenant(db_session, "ss-tenant-b1")
    tenant_b = await _seed_tenant(db_session, "ss-tenant-b2")
    theme = (await SqlAlchemyThemeRepository(db_session).list())[0]
    repo = SqlAlchemyStoreSettingsRepository(db_session)

    settings_a = StoreSettings(tenant_id=tenant_a.id, theme_id=theme.id, store_name="Store A")
    settings_b = StoreSettings(tenant_id=tenant_b.id, theme_id=theme.id, store_name="Store B")
    await repo.upsert(settings_a)
    await repo.upsert(settings_b)
    await db_session.commit()

    fetched_a = await repo.get_by_tenant(tenant_a.id)
    fetched_b = await repo.get_by_tenant(tenant_b.id)

    assert fetched_a is not None and fetched_a.store_name == "Store A"
    assert fetched_b is not None and fetched_b.store_name == "Store B"
    assert fetched_a.id != fetched_b.id
