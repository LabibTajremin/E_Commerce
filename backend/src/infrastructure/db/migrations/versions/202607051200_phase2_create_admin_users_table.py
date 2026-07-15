"""phase2 create admin_users table with rls

Revision ID: 202607051200
Revises: 202607050900
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607051200"
down_revision = "202607050900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_users",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "tenant_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False, server_default="owner"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint(
        "uq_admin_users_tenant_email", "admin_users", ["tenant_id", "email"]
    )
    # Every login/registration flow looks up a user by (tenant_id, email); this
    # composite index also backs the unique constraint above.
    op.create_index("ix_admin_users_tenant_id", "admin_users", ["tenant_id"])

    op.execute("ALTER TABLE admin_users ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_admin_users ON admin_users
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_admin_users ON admin_users;")
    op.drop_index("ix_admin_users_tenant_id", table_name="admin_users")
    op.drop_constraint("uq_admin_users_tenant_email", "admin_users", type_="unique")
    op.drop_table("admin_users")
