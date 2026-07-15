"""phase1 create tenants table

Revision ID: 202607050900
Revises:
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607050900"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("subdomain", sa.String(63), nullable=False, unique=True),
        sa.Column("custom_domain", sa.String(255), nullable=True, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="trial"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # Hottest lookup on every storefront request: resolve tenant by subdomain.
    op.create_index("ix_tenants_subdomain", "tenants", ["subdomain"])
    # Second hottest lookup: resolve tenant by mapped custom domain (Phase 11).
    op.create_index("ix_tenants_custom_domain", "tenants", ["custom_domain"])
    # Superadmin dashboard filters tenants by status frequently.
    op.create_index("ix_tenants_status", "tenants", ["status"])


def downgrade() -> None:
    op.drop_index("ix_tenants_status", table_name="tenants")
    op.drop_index("ix_tenants_custom_domain", table_name="tenants")
    op.drop_index("ix_tenants_subdomain", table_name="tenants")
    op.drop_table("tenants")
