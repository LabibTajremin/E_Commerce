import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base


class StoreSettingsModel(Base):
    __tablename__ = "store_settings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    theme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("themes.id"), nullable=False
    )
    store_name: Mapped[str] = mapped_column(String(255), nullable=False, server_default="")
    logo_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    primary_color: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#111827")
    accent_color: Mapped[str] = mapped_column(String(7), nullable=False, server_default="#2563eb")
    font_choice: Mapped[str] = mapped_column(String(100), nullable=False, server_default="Inter")
    banner_images: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    announcement_bar_text: Mapped[str | None] = mapped_column(String(500), nullable=True)
    social_links: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    seo_meta: Mapped[dict[str, str]] = mapped_column(JSON, nullable=False, default=dict)
    enabled_sections: Mapped[dict[str, bool]] = mapped_column(JSON, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
