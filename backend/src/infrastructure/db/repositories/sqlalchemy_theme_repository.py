from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.entities.theme import Theme, ThemeLayoutType
from src.infrastructure.db.models.theme import ThemeModel


class SqlAlchemyThemeRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_entity(self, model: ThemeModel) -> Theme:
        return Theme(
            id=model.id,
            name=model.name,
            layout_type=ThemeLayoutType(model.layout_type),
            sections=dict(model.sections),
        )

    async def get_by_id(self, theme_id: UUID) -> Theme | None:
        model = await self._session.get(ThemeModel, theme_id)
        return self._to_entity(model) if model else None

    async def list(self) -> list[Theme]:
        result = await self._session.execute(select(ThemeModel).order_by(ThemeModel.name))
        return [self._to_entity(m) for m in result.scalars().all()]
