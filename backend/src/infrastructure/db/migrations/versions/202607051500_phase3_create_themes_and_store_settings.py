"""phase3 create themes and store_settings tables with rls

Revision ID: 202607051500
Revises: 202607051200
Create Date: 2026-07-05
"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql as pg

revision = "202607051500"
down_revision = "202607051200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "themes",
        sa.Column(
            "id",
            pg.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("layout_type", sa.String(20), nullable=False),
        sa.Column("sections", pg.JSON, nullable=False),
    )

    op.create_table(
        "store_settings",
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
        sa.Column("theme_id", pg.UUID(as_uuid=True), sa.ForeignKey("themes.id"), nullable=False),
        sa.Column("store_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("logo_url", sa.String(2048), nullable=True),
        sa.Column("favicon_url", sa.String(2048), nullable=True),
        sa.Column("primary_color", sa.String(7), nullable=False, server_default="#111827"),
        sa.Column("accent_color", sa.String(7), nullable=False, server_default="#2563eb"),
        sa.Column("font_choice", sa.String(100), nullable=False, server_default="Inter"),
        sa.Column("banner_images", pg.JSON, nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("announcement_bar_text", sa.String(500), nullable=True),
        sa.Column("social_links", pg.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("seo_meta", pg.JSON, nullable=False, server_default=sa.text("'{}'::json")),
        sa.Column("enabled_sections", pg.JSON, nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )
    # tenant_id already carries a unique constraint (one settings row per store);
    # this index is what every storefront/admin request filters on.
    op.create_index("ix_store_settings_tenant_id", "store_settings", ["tenant_id"])

    op.execute("ALTER TABLE store_settings ENABLE ROW LEVEL SECURITY;")
    op.execute(
        """
        CREATE POLICY tenant_isolation_store_settings ON store_settings
        USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation_store_settings ON store_settings;")
    op.drop_index("ix_store_settings_tenant_id", table_name="store_settings")
    op.drop_table("store_settings")
    op.drop_table("themes")
