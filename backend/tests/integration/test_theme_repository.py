from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.db.repositories.sqlalchemy_theme_repository import (
    SqlAlchemyThemeRepository,
)


async def test_list_returns_seeded_starter_themes(db_session: AsyncSession) -> None:
    repo = SqlAlchemyThemeRepository(db_session)

    themes = await repo.list()

    names = {t.name for t in themes}
    assert {"Grid Storefront", "Minimal", "Classic Catalog"}.issubset(names)


async def test_get_by_id_returns_seeded_theme(db_session: AsyncSession) -> None:
    repo = SqlAlchemyThemeRepository(db_session)
    themes = await repo.list()
    first = themes[0]

    found = await repo.get_by_id(first.id)

    assert found is not None
    assert found.name == first.name
    assert found.sections == first.sections
