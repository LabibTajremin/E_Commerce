import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base


class CartModel(Base):
    __tablename__ = "carts"
    # updated_at has no client-side default, only onupdate=func.now() — without
    # eager_defaults, an UPDATE flush leaves it expired rather than refreshed
    # via RETURNING, and the plain attribute read in _to_entity() then tries
    # an implicit lazy-load, which the async ORM can't do outside its
    # greenlet bridge (raises MissingGreenlet). INSERT isn't affected since
    # Postgres RETURNING already populates it there.
    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    customer_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("customers.id", ondelete="CASCADE"), nullable=True
    )
    session_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line_items: Mapped[list[dict[str, object]]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
