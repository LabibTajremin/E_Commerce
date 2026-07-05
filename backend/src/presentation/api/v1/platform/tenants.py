from uuid import UUID

from fastapi import APIRouter, Query, status

from src.application.use_cases.tenants.create_tenant import (
    CreateTenantInput,
    CreateTenantUseCase,
)
from src.application.use_cases.tenants.list_tenants import ListTenantsUseCase
from src.application.use_cases.tenants.suspend_tenant import (
    ReactivateTenantUseCase,
    SuspendTenantUseCase,
)
from src.domain.entities.tenant import TenantStatus
from src.domain.repositories.tenant_repository import TenantFilters
from src.presentation.dependencies import TenantRepositoryDep
from src.presentation.schemas.tenant import TenantCreateRequest, TenantResponse

router = APIRouter(prefix="/tenants", tags=["platform:tenants"])


@router.post("", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
async def create_tenant(
    body: TenantCreateRequest, tenant_repository: TenantRepositoryDep
) -> TenantResponse:
    use_case = CreateTenantUseCase(tenant_repository)
    tenant = await use_case.execute(
        CreateTenantInput(
            name=body.name, subdomain=body.subdomain, custom_domain=body.custom_domain
        )
    )
    return TenantResponse.from_entity(tenant)


@router.get("", response_model=list[TenantResponse])
async def list_tenants(
    tenant_repository: TenantRepositoryDep,
    status_filter: TenantStatus | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
) -> list[TenantResponse]:
    use_case = ListTenantsUseCase(tenant_repository)
    tenants = await use_case.execute(
        TenantFilters(status=status_filter, search=search, limit=limit, offset=offset)
    )
    return [TenantResponse.from_entity(t) for t in tenants]


@router.post("/{tenant_id}/suspend", response_model=TenantResponse)
async def suspend_tenant(tenant_id: UUID, tenant_repository: TenantRepositoryDep) -> TenantResponse:
    use_case = SuspendTenantUseCase(tenant_repository)
    tenant = await use_case.execute(tenant_id)
    return TenantResponse.from_entity(tenant)


@router.post("/{tenant_id}/reactivate", response_model=TenantResponse)
async def reactivate_tenant(
    tenant_id: UUID, tenant_repository: TenantRepositoryDep
) -> TenantResponse:
    use_case = ReactivateTenantUseCase(tenant_repository)
    tenant = await use_case.execute(tenant_id)
    return TenantResponse.from_entity(tenant)
