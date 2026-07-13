"""phase3 seed starter themes

Revision ID: 202607051501
Revises: 202607051500
Create Date: 2026-07-05
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607051501"
down_revision = "202607051500"
branch_labels = None
depends_on = None

_THEMES_TABLE = sa.table(
    "themes",
    sa.column("id", pg.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("layout_type", sa.String),
    sa.column("sections", pg.JSON),
)

_STARTER_THEMES = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000001"),
        "name": "Grid Storefront",
        "layout_type": "grid",
        "sections": {
            "hero_banner": True,
            "featured_products": True,
            "testimonials": False,
            "footer": True,
        },
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000002"),
        "name": "Minimal",
        "layout_type": "minimal",
        "sections": {
            "hero_banner": False,
            "featured_products": True,
            "testimonials": False,
            "footer": True,
        },
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-000000000003"),
        "name": "Classic Catalog",
        "layout_type": "classic",
        "sections": {
            "hero_banner": True,
            "featured_products": True,
            "testimonials": True,
            "footer": True,
        },
    },
]


def upgrade() -> None:
    # sections is a pg.JSON column — op.bulk_insert already runs values
    # through that type's bind processor (which itself calls json.dumps()),
    # so passing an already-json.dumps()'d string here double-encodes it:
    # reading it back gives a JSON string containing another JSON string,
    # not a dict.
    op.bulk_insert(_THEMES_TABLE, _STARTER_THEMES)


def downgrade() -> None:
    ids = tuple(str(t["id"]) for t in _STARTER_THEMES)
    op.execute(f"DELETE FROM themes WHERE id IN {ids}")
