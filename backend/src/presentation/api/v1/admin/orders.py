from uuid import UUID

from fastapi import APIRouter, Query

from src.application.use_cases.orders.manage_orders import (
    GetOrderUseCase,
    ListOrdersUseCase,
    UpdateOrderStatusInput,
    UpdateOrderStatusUseCase,
)
from src.domain.entities.order import OrderStatus
from src.domain.repositories.order_repository import OrderFilters
from src.presentation.dependencies import CurrentAdminDep, OrderRepositoryDep
from src.presentation.schemas.order import (
    OrderPageResponse,
    OrderResponse,
    UpdateOrderStatusRequest,
)

router = APIRouter(prefix="/orders", tags=["admin:orders"])


@router.get("", response_model=OrderPageResponse)
async def list_orders(
    current: CurrentAdminDep,
    order_repository: OrderRepositoryDep,
    status_filter: OrderStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> OrderPageResponse:
    use_case = ListOrdersUseCase(order_repository)
    page = await use_case.execute(
        current.tenant_id, OrderFilters(status=status_filter, limit=limit, offset=offset)
    )
    return OrderPageResponse(
        items=[OrderResponse.from_entity(o) for o in page.items], total=page.total
    )


@router.get("/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: UUID, current: CurrentAdminDep, order_repository: OrderRepositoryDep
) -> OrderResponse:
    use_case = GetOrderUseCase(order_repository)
    order = await use_case.execute(current.tenant_id, order_id)
    return OrderResponse.from_entity(order)


@router.patch("/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: UUID,
    body: UpdateOrderStatusRequest,
    current: CurrentAdminDep,
    order_repository: OrderRepositoryDep,
) -> OrderResponse:
    use_case = UpdateOrderStatusUseCase(order_repository)
    order = await use_case.execute(
        UpdateOrderStatusInput(
            tenant_id=current.tenant_id, order_id=order_id, new_status=body.status
        )
    )
    return OrderResponse.from_entity(order)
