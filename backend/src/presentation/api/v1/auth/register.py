from fastapi import APIRouter, status

from src.application.use_cases.auth.register_tenant_owner import (
    RegisterTenantOwnerInput,
    RegisterTenantOwnerUseCase,
)
from src.presentation.dependencies import UnitOfWorkDep
from src.presentation.schemas.auth import RegisterTenantOwnerRequest, RegisterTenantOwnerResponse

router = APIRouter(tags=["auth:register"])


@router.post(
    "/register", response_model=RegisterTenantOwnerResponse, status_code=status.HTTP_201_CREATED
)
async def register_tenant_owner(
    body: RegisterTenantOwnerRequest, uow: UnitOfWorkDep
) -> RegisterTenantOwnerResponse:
    use_case = RegisterTenantOwnerUseCase(uow)
    result = await use_case.execute(
        RegisterTenantOwnerInput(
            tenant_name=body.tenant_name,
            subdomain=body.subdomain,
            owner_email=body.owner_email,
            owner_password=body.owner_password,
        )
    )
    return RegisterTenantOwnerResponse(
        tenant_id=result.tenant.id,
        owner_id=result.owner.id,
        subdomain=str(result.tenant.subdomain),
    )
