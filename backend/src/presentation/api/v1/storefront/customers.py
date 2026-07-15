from fastapi import APIRouter, status

from src.application.use_cases.customers.login_customer import (
    LoginCustomerInput,
    LoginCustomerUseCase,
)
from src.application.use_cases.customers.register_customer import (
    RegisterCustomerInput,
    RegisterCustomerUseCase,
)
from src.presentation.dependencies import (
    ClientIpDep,
    CustomerRepositoryDep,
    MasterPasswordGateDep,
    RateLimiterDep,
    ResolvedTenantIdDep,
)
from src.presentation.schemas.auth import TokenPairResponse
from src.presentation.schemas.customer import LoginCustomerRequest, RegisterCustomerRequest

router = APIRouter(prefix="/customers", tags=["storefront:customers"])


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenPairResponse)
async def register_customer(
    body: RegisterCustomerRequest,
    tenant_id: ResolvedTenantIdDep,
    customer_repository: CustomerRepositoryDep,
    rate_limiter: RateLimiterDep,
    master_password_gate: MasterPasswordGateDep,
    client_ip: ClientIpDep,
) -> TokenPairResponse:
    assert tenant_id is not None
    register_use_case = RegisterCustomerUseCase(customer_repository)
    await register_use_case.execute(
        RegisterCustomerInput(
            tenant_id=tenant_id, email=body.email, password=body.password, name=body.name
        )
    )
    login_use_case = LoginCustomerUseCase(customer_repository, rate_limiter, master_password_gate)
    tokens = await login_use_case.execute(
        LoginCustomerInput(
            tenant_id=tenant_id, email=body.email, password=body.password, ip_address=client_ip
        )
    )
    return TokenPairResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)


@router.post("/login", response_model=TokenPairResponse)
async def login_customer(
    body: LoginCustomerRequest,
    tenant_id: ResolvedTenantIdDep,
    customer_repository: CustomerRepositoryDep,
    rate_limiter: RateLimiterDep,
    master_password_gate: MasterPasswordGateDep,
    client_ip: ClientIpDep,
) -> TokenPairResponse:
    assert tenant_id is not None
    use_case = LoginCustomerUseCase(customer_repository, rate_limiter, master_password_gate)
    tokens = await use_case.execute(
        LoginCustomerInput(
            tenant_id=tenant_id, email=body.email, password=body.password, ip_address=client_ip
        )
    )
    return TokenPairResponse(access_token=tokens.access_token, refresh_token=tokens.refresh_token)
