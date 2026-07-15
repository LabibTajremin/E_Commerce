import uuid
from decimal import Decimal

from sqlalchemy import Boolean, Integer, Numeric, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from src.infrastructure.db.session import Base


class SubscriptionPlanModel(Base):
    __tablename__ = "subscription_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_products: Mapped[int] = mapped_column(Integer, nullable=False)
    max_banners: Mapped[int] = mapped_column(Integer, nullable=False)
    custom_domain_allowed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default="false"
    )
    stripe_price_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
