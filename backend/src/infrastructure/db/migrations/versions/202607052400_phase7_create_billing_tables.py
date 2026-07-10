"""phase7 create subscription_plans, tenant_subscriptions, processed_webhook_events

Revision ID: 202607052400
Revises: 202607052300
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607052400"
down_revision = "202607052300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "subscription_plans",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("max_products", sa.Integer(), nullable=False),
        sa.Column("max_banners", sa.Integer(), nullable=False),
        sa.Column("custom_domain_allowed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("stripe_price_id", sa.String(255), nullable=True),
    )

    op.create_table(
        "tenant_subscriptions",
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
            unique=True,
        ),
        sa.Column(
            "plan_id", pg.UUID(as_uuid=True), sa.ForeignKey("subscription_plans.id"), nullable=False
        ),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=True, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="trialing"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_tenant_subscriptions_tenant_id", "tenant_subscriptions", ["tenant_id"]
    )
    op.execute("ALTER TABLE tenant_subscriptions ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_tenant_subscriptions ON tenant_subscriptions
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )

    op.create_table(
        "processed_webhook_events",
        sa.Column("event_id", sa.String(255), primary_key=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    op.drop_table("processed_webhook_events")

    op.execute(
        "DROP POLICY IF EXISTS tenant_isolation_tenant_subscriptions ON tenant_subscriptions;"
    )
    op.drop_index("ix_tenant_subscriptions_tenant_id", table_name="tenant_subscriptions")
    op.drop_table("tenant_subscriptions")

    op.drop_table("subscription_plans")
