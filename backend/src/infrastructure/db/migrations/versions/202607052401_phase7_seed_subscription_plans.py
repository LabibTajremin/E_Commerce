"""phase7 seed starter subscription plans

Revision ID: 202607052401
Revises: 202607052400
Create Date: 2026-07-05
"""
import uuid

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607052401"
down_revision = "202607052400"
branch_labels = None
depends_on = None

_PLANS_TABLE = sa.table(
    "subscription_plans",
    sa.column("id", pg.UUID(as_uuid=True)),
    sa.column("name", sa.String),
    sa.column("price", sa.Numeric),
    sa.column("max_products", sa.Integer),
    sa.column("max_banners", sa.Integer),
    sa.column("custom_domain_allowed", sa.Boolean),
)

_STARTER_PLANS = [
    {
        "id": uuid.UUID("00000000-0000-0000-0000-0000000000a1"),
        "name": "Starter",
        "price": "0.00",
        "max_products": 25,
        "max_banners": 2,
        "custom_domain_allowed": False,
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-0000000000a2"),
        "name": "Growth",
        "price": "29.00",
        "max_products": 500,
        "max_banners": 5,
        "custom_domain_allowed": False,
    },
    {
        "id": uuid.UUID("00000000-0000-0000-0000-0000000000a3"),
        "name": "Scale",
        "price": "99.00",
        "max_products": 50000,
        "max_banners": 10,
        "custom_domain_allowed": True,
    },
]


def upgrade() -> None:
    op.bulk_insert(_PLANS_TABLE, _STARTER_PLANS)


def downgrade() -> None:
    ids = tuple(str(p["id"]) for p in _STARTER_PLANS)
    op.execute(f"DELETE FROM subscription_plans WHERE id IN {ids}")
