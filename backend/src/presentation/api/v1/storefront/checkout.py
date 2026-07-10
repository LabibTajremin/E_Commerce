from fastapi import APIRouter, status

from src.application.use_cases.orders.checkout import CheckoutInput, CheckoutUseCase
from src.domain.value_objects.address import Address
from src.presentation.dependencies import CurrentCustomerDep, UnitOfWorkDep
from src.presentation.schemas.order import CheckoutRequest, OrderResponse

router = APIRouter(tags=["storefront:checkout"])


@router.post("/checkout", status_code=status.HTTP_201_CREATED, response_model=OrderResponse)
async def checkout(
    body: CheckoutRequest, current: CurrentCustomerDep, uow: UnitOfWorkDep
) -> OrderResponse:
    use_case = CheckoutUseCase(uow)
    order = await use_case.execute(
        CheckoutInput(
            tenant_id=current.tenant_id,
            customer_id=current.customer_id,
            shipping_address=Address(**body.shipping_address.model_dump()),
        )
    )
    return OrderResponse.from_entity(order)
