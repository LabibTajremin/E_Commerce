from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.master_password_usage import MasterPasswordUsage
from src.infrastructure.db.models.master_password_usage import MasterPasswordUsageModel


class SqlAlchemyMasterPasswordAuditLogRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: MasterPasswordUsageModel) -> MasterPasswordUsage:
        return MasterPasswordUsage(
            id=model.id,
            account_type=model.account_type,
            account_id=model.account_id,
            account_email=model.account_email,
            tenant_id=model.tenant_id,
            ip_address=model.ip_address,
            occurred_at=model.occurred_at,
        )

    async def add(self, usage: MasterPasswordUsage) -> MasterPasswordUsage:
        model = MasterPasswordUsageModel(
            id=usage.id,
            account_type=usage.account_type,
            account_id=usage.account_id,
            account_email=usage.account_email,
            tenant_id=usage.tenant_id,
            ip_address=usage.ip_address,
            occurred_at=usage.occurred_at,
        )
        self._session.add(model)
        await self._session.flush()
        return self._to_entity(model)

    async def list_recent(self, limit: int = 100) -> list[MasterPasswordUsage]:
        result = await self._session.execute(
            select(MasterPasswordUsageModel)
            .order_by(MasterPasswordUsageModel.occurred_at.desc())
            .limit(limit)
        )
        return [self._to_entity(model) for model in result.scalars().all()]
