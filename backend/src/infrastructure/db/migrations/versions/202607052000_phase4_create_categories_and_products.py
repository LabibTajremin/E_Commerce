"""phase4 create categories and products tables with rls and search index

Revision ID: 202607052000
Revises: 202607051501
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607052000"
down_revision = "202607051501"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "categories",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column(
            "parent_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_unique_constraint("uq_categories_tenant_slug", "categories", ["tenant_id", "slug"])
    op.create_index("ix_categories_tenant_id", "categories", ["tenant_id"])

    op.execute("ALTER TABLE categories ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_categories ON categories
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )

    op.create_table(
        "products",
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
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("compare_at_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("sku", sa.String(50), nullable=True),
        sa.Column("images", pg.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("stock_qty", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column(
            "category_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "search_vector",
            pg.TSVECTOR,
            sa.Computed(
                "to_tsvector('english', coalesce(name, '') || ' ' || coalesce(description, ''))",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_unique_constraint("uq_products_tenant_slug", "products", ["tenant_id", "slug"])
    # (tenant_id, slug) lookups (product detail by slug) are covered by the unique
    # constraint's implicit index. The rest back the storefront/admin's other
    # most common queries:
    op.create_index("ix_products_tenant_id", "products", ["tenant_id"])
    # "list published products for tenant X" — the single hottest storefront query.
    op.create_index("ix_products_tenant_status", "products", ["tenant_id", "status"])
    # category-filtered browsing.
    op.create_index("ix_products_tenant_category", "products", ["tenant_id", "category_id"])
    # SKU is unique per tenant (Section 4); NULLs are exempt from the constraint,
    # so products without a SKU yet don't collide with each other.
    op.create_unique_constraint("uq_products_tenant_sku", "products", ["tenant_id", "sku"])
    # full-text search on name/description.
    op.execute(
        "CREATE INDEX ix_products_search_vector ON products USING GIN (search_vector);"
    )

    op.execute("ALTER TABLE products ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_products ON products
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_products ON products;")
    op.execute("DROP INDEX IF EXISTS ix_products_search_vector;")
    op.drop_constraint("uq_products_tenant_sku", "products", type_="unique")
    op.drop_index("ix_products_tenant_category", table_name="products")
    op.drop_index("ix_products_tenant_status", table_name="products")
    op.drop_index("ix_products_tenant_id", table_name="products")
    op.drop_constraint("uq_products_tenant_slug", "products", type_="unique")
    op.drop_table("products")

    op.execute("DROP POLICY IF EXISTS tenant_isolation_categories ON categories;")
    op.drop_index("ix_categories_tenant_id", table_name="categories")
    op.drop_constraint("uq_categories_tenant_slug", "categories", type_="unique")
    op.drop_table("categories")
