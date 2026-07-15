from uuid import UUID

from fastapi import APIRouter

from src.application.use_cases.billing.create_order_checkout_session import (
    CreateOrderCheckoutSessionInput,
    CreateOrderCheckoutSessionUseCase,
)
from src.application.use_cases.orders.manage_orders import GetOrderUseCase, ListOrdersUseCase
from src.domain.exceptions import PermissionDeniedError
from src.domain.repositories.order_repository import OrderFilters
from src.presentation.dependencies import CurrentCustomerDep, OrderRepositoryDep, PaymentGatewayDep
from src.presentation.schemas.billing import CheckoutUrlResponse, PayOrderRequest
from src.presentation.schemas.order import OrderPageResponse, OrderResponse

router = APIRouter(prefix="/orders", tags=["storefront:orders"])


@router.get("", response_model=OrderPageResponse)
async def list_my_orders(
    current: CurrentCustomerDep, order_repository: OrderRepositoryDep
) -> OrderPageResponse:
    use_case = ListOrdersUseCase(order_repository)
    page = await use_case.execute(
        current.tenant_id, OrderFilters(customer_id=current.customer_id)
    )
    return OrderPageResponse(
        items=[OrderResponse.from_entity(o) for o in page.items], total=page.total
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_my_order(
    order_id: UUID, current: CurrentCustomerDep, order_repository: OrderRepositoryDep
) -> OrderResponse:
    use_case = GetOrderUseCase(order_repository)
    order = await use_case.execute(current.tenant_id, order_id)
    if order.customer_id != current.customer_id:
        raise PermissionDeniedError("Not your order")
    return OrderResponse.from_entity(order)


@router.post("/{order_id}/pay", response_model=CheckoutUrlResponse)
async def pay_order(
    order_id: UUID,
    body: PayOrderRequest,
    current: CurrentCustomerDep,
    order_repository: OrderRepositoryDep,
    payment_gateway: PaymentGatewayDep,
) -> CheckoutUrlResponse:
    get_use_case = GetOrderUseCase(order_repository)
    order = await get_use_case.execute(current.tenant_id, order_id)
    if order.customer_id != current.customer_id:
        raise PermissionDeniedError("Not your order")

    use_case = CreateOrderCheckoutSessionUseCase(order_repository, payment_gateway)
    url = await use_case.execute(
        CreateOrderCheckoutSessionInput(
            tenant_id=current.tenant_id,
            order_id=order_id,
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    )
    return CheckoutUrlResponse(checkout_url=url)
