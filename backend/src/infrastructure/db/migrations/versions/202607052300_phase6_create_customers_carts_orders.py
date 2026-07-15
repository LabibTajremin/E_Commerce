"""phase6 create customers, carts, orders, order_line_items with rls

Revision ID: 202607052300
Revises: 202607052000
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607052300"
down_revision = "202607052000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "customers",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("addresses", pg.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    op.create_unique_constraint("uq_customers_tenant_email", "customers", ["tenant_id", "email"])
    op.create_index("ix_customers_tenant_id", "customers", ["tenant_id"])
    op.execute("ALTER TABLE customers ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_customers ON customers
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )

    op.create_table(
        "carts",
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
        sa.Column(
            "customer_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("line_items", pg.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # One active cart per authenticated customer / anonymous session.
    op.create_index(
        "ux_carts_tenant_customer",
        "carts",
        ["tenant_id", "customer_id"],
        unique=True,
        postgresql_where=sa.text("customer_id IS NOT NULL"),
    )
    op.create_index(
        "ux_carts_tenant_session",
        "carts",
        ["tenant_id", "session_id"],
        unique=True,
        postgresql_where=sa.text("session_id IS NOT NULL"),
    )
    op.execute("ALTER TABLE carts ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_carts ON carts
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )

    op.create_table(
        "orders",
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
        sa.Column(
            "customer_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("customers.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"),
        sa.Column("subtotal", sa.Numeric(10, 2), nullable=False),
        sa.Column("tax", sa.Numeric(10, 2), nullable=False),
        sa.Column("shipping", sa.Numeric(10, 2), nullable=False),
        sa.Column("total", sa.Numeric(10, 2), nullable=False),
        sa.Column("shipping_address", pg.JSON, nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # "list this customer's orders" and "list orders by status" (admin fulfillment
    # queue) are the two hottest order queries.
    op.create_index("ix_orders_tenant_customer", "orders", ["tenant_id", "customer_id"])
    op.create_index("ix_orders_tenant_status", "orders", ["tenant_id", "status"])
    op.execute("ALTER TABLE orders ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_orders ON orders
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )

    op.create_table(
        "order_line_items",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "order_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("product_id", pg.UUID(as_uuid=True), nullable=False),
        sa.Column("product_name", sa.String(255), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
    )
    op.create_index("ix_order_line_items_order_id", "order_line_items", ["order_id"])
    # order_line_items has no tenant_id of its own — it's only ever reached
    # through its parent order, which is itself RLS-protected.


def downgrade() -> None:
    op.drop_index("ix_order_line_items_order_id", table_name="order_line_items")
    op.drop_table("order_line_items")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_orders ON orders;")
    op.drop_index("ix_orders_tenant_status", table_name="orders")
    op.drop_index("ix_orders_tenant_customer", table_name="orders")
    op.drop_table("orders")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_carts ON carts;")
    op.drop_index("ux_carts_tenant_session", table_name="carts")
    op.drop_index("ux_carts_tenant_customer", table_name="carts")
    op.drop_table("carts")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_customers ON customers;")
    op.drop_index("ix_customers_tenant_id", table_name="customers")
    op.drop_constraint("uq_customers_tenant_email", "customers", type_="unique")
    op.drop_table("customers")
