"""phase8 create platform_admins table

Revision ID: 202607052500
Revises: 202607052401
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607052500"
down_revision = "202607052401"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Global, not tenant-scoped — superadmins operate across all tenants, so
    # no tenant_id column and no RLS policy here (unlike every other table).
    op.create_table(
        "platform_admins",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index("ix_platform_admins_email", "platform_admins", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_platform_admins_email", table_name="platform_admins")
    op.drop_table("platform_admins")
