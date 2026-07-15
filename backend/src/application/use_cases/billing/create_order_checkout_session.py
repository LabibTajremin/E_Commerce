from dataclasses import dataclass
from uuid import UUID

from src.application.interfaces.payment_gateway import PaymentGateway
from src.domain.entities.order import OrderStatus
from src.domain.exceptions import EntityNotFoundError, ValidationError
from src.domain.repositories.order_repository import OrderRepository


@dataclass(frozen=True, slots=True)
class CreateOrderCheckoutSessionInput:
    tenant_id: UUID
    order_id: UUID
    success_url: str
    cancel_url: str


class CreateOrderCheckoutSessionUseCase:
    def __init__(self, order_repository: OrderRepository, payment_gateway: PaymentGateway) -> None:
        self._orders = order_repository
        self._gateway = payment_gateway

    async def execute(self, data: CreateOrderCheckoutSessionInput) -> str:
        order = await self._orders.get_by_id(data.tenant_id, data.order_id)
        if order is None:
            raise EntityNotFoundError("Order", data.order_id)
        if order.status != OrderStatus.PENDING:
            raise ValidationError(f"Order is not payable in status {order.status}")

        amount_cents = int(order.total * 100)
        return await self._gateway.create_order_checkout_session(
            tenant_id=str(data.tenant_id),
            order_id=str(order.id),
            amount_cents=amount_cents,
            currency="usd",
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )
