from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.tenant import Tenant, TenantStatus
from src.domain.repositories.tenant_repository import TenantFilters
from src.domain.value_objects.subdomain import Subdomain
from src.infrastructure.db.models.tenant import TenantModel


class SqlAlchemyTenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: TenantModel) -> Tenant:
        return Tenant(
            id=model.id,
            name=model.name,
            subdomain=Subdomain(model.subdomain),
            custom_domain=model.custom_domain,
            status=TenantStatus(model.status),
            created_at=model.created_at,
        )

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        model = await self._session.get(TenantModel, tenant_id)
        return self._to_entity(model) if model else None

    async def get_by_subdomain(self, subdomain: str) -> Tenant | None:
        result = await self._session.execute(
            select(TenantModel).where(TenantModel.subdomain == subdomain)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def get_by_custom_domain(self, custom_domain: str) -> Tenant | None:
        result = await self._session.execute(
            select(TenantModel).where(TenantModel.custom_domain == custom_domain)
        )
        model = result.scalar_one_or_none()
        return self._to_entity(model) if model else None

    async def list(self, filters: TenantFilters) -> list[Tenant]:
        query = select(TenantModel)
        if filters.status is not None:
            query = query.where(TenantModel.status == filters.status.value)
        if filters.search:
            like = f"%{filters.search}%"
            query = query.where(
                or_(TenantModel.name.ilike(like), TenantModel.subdomain.ilike(like))
            )
        query = query.order_by(TenantModel.created_at.desc()).limit(filters.limit).offset(
            filters.offset
        )
        result = await self._session.execute(query)
        return [self._to_entity(m) for m in result.scalars().all()]

    async def add(self, tenant: Tenant) -> Tenant:
        model = TenantModel(
            id=tenant.id,
            name=tenant.name,
            subdomain=str(tenant.subdomain),
            custom_domain=tenant.custom_domain,
            status=tenant.status.value,
            created_at=tenant.created_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def update(self, tenant: Tenant) -> Tenant:
        model = await self._session.get(TenantModel, tenant.id)
        if model is None:
            raise ValueError(f"Tenant not found: {tenant.id}")
        model.name = tenant.name
        model.subdomain = str(tenant.subdomain)
        model.custom_domain = tenant.custom_domain
        model.status = tenant.status.value
        await self._session.flush()
        return self._to_entity(model)
