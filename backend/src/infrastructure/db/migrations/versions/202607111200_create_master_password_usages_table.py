"""create master_password_usages table

Revision ID: 202607111200
Revises: 202607052500
Create Date: 2026-07-11
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607111200"
down_revision = "202607052500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Global, not tenant-scoped — a master-password login can authenticate
    # into any tenant's account, so this audit trail isn't RLS-restricted to
    # one tenant either (same reasoning as platform_admins).
    op.create_table(
        "master_password_usages",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("account_type", sa.String(32), nullable=False),
        sa.Column("account_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("account_email", sa.String(255), nullable=False),
        sa.Column("tenant_id", pg.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(64), nullable=False),
        sa.Column(
            "occurred_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_index(
        "ix_master_password_usages_occurred_at", "master_password_usages", ["occurred_at"]
    )


def downgrade() -> None:
    op.drop_index("ix_master_password_usages_occurred_at", table_name="master_password_usages")
    op.drop_table("master_password_usages")
