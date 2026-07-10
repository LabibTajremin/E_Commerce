from fastapi import APIRouter

from src.application.use_cases.billing.create_subscription_checkout import (
    CreateSubscriptionCheckoutInput,
    CreateSubscriptionCheckoutUseCase,
)
from src.domain.exceptions import EntityNotFoundError
from src.presentation.dependencies import (
    AdminUserRepositoryDep,
    CurrentAdminDep,
    PaymentGatewayDep,
    SubscriptionPlanRepositoryDep,
    TenantSubscriptionRepositoryDep,
)
from src.presentation.schemas.billing import (
    CheckoutUrlResponse,
    SubscribeRequest,
    SubscriptionPlanResponse,
    TenantSubscriptionResponse,
)

router = APIRouter(prefix="/billing", tags=["admin:billing"])


@router.get("/plans", response_model=list[SubscriptionPlanResponse])
async def list_plans(
    current: CurrentAdminDep, plan_repository: SubscriptionPlanRepositoryDep
) -> list[SubscriptionPlanResponse]:
    del current
    plans = await plan_repository.list()
    return [SubscriptionPlanResponse.from_entity(p) for p in plans]


@router.get("/subscription", response_model=TenantSubscriptionResponse | None)
async def get_subscription(
    current: CurrentAdminDep, subscription_repository: TenantSubscriptionRepositoryDep
) -> TenantSubscriptionResponse | None:
    subscription = await subscription_repository.get_by_tenant(current.tenant_id)
    return TenantSubscriptionResponse.from_entity(subscription) if subscription else None


@router.post("/subscribe", response_model=CheckoutUrlResponse)
async def subscribe(
    body: SubscribeRequest,
    current: CurrentAdminDep,
    plan_repository: SubscriptionPlanRepositoryDep,
    subscription_repository: TenantSubscriptionRepositoryDep,
    payment_gateway: PaymentGatewayDep,
    admin_user_repository: AdminUserRepositoryDep,
) -> CheckoutUrlResponse:
    plan = await plan_repository.get_by_id(body.plan_id)
    if plan is None:
        raise EntityNotFoundError("SubscriptionPlan", body.plan_id)
    admin_user = await admin_user_repository.get_by_id(current.tenant_id, current.user_id)
    if admin_user is None:
        raise EntityNotFoundError("AdminUser", current.user_id)

    use_case = CreateSubscriptionCheckoutUseCase(
        plan_repository, subscription_repository, payment_gateway
    )
    url = await use_case.execute(
        CreateSubscriptionCheckoutInput(
            tenant_id=current.tenant_id,
            plan_id=body.plan_id,
            owner_email=str(admin_user.email),
            success_url=body.success_url,
            cancel_url=body.cancel_url,
        )
    )
    return CheckoutUrlResponse(checkout_url=url)
