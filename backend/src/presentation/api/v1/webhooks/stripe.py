from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse

from src.application.use_cases.billing.process_stripe_webhook import (
    ProcessStripeWebhookInput,
    ProcessStripeWebhookUseCase,
)
from src.domain.exceptions import AuthenticationError
from src.presentation.dependencies import PaymentGatewayDep, UnitOfWorkDep

router = APIRouter(prefix="/webhooks", tags=["webhooks:stripe"])


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    payment_gateway: PaymentGatewayDep,
    uow: UnitOfWorkDep,
    stripe_signature: str | None = Header(default=None, alias="stripe-signature"),
) -> JSONResponse:
    if stripe_signature is None:
        raise AuthenticationError("Missing Stripe-Signature header")

    payload = await request.body()
    use_case = ProcessStripeWebhookUseCase(payment_gateway, uow)
    result = await use_case.execute(
        ProcessStripeWebhookInput(payload=payload, signature_header=stripe_signature)
    )
    return JSONResponse(content={"status": result})
