from uuid import UUID

from fastapi import APIRouter

from src.application.use_cases.orders.manage_orders import GetOrderUseCase, ListOrdersUseCase
from src.domain.exceptions import PermissionDeniedError
from src.domain.repositories.order_repository import OrderFilters
from src.presentation.dependencies import CurrentCustomerDep, OrderRepositoryDep
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
