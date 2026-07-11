from fastapi import APIRouter, Depends, Query

from src.application.use_cases.platform.list_master_password_usages import (
    ListMasterPasswordUsagesUseCase,
)
from src.presentation.dependencies import (
    MasterPasswordAuditLogRepositoryDep,
    require_platform_admin,
)
from src.presentation.schemas.master_password_audit import MasterPasswordUsageResponse

router = APIRouter(
    prefix="/master-password-usages",
    tags=["platform:master-password-audit"],
    dependencies=[Depends(require_platform_admin)],
)


@router.get("", response_model=list[MasterPasswordUsageResponse])
async def list_master_password_usages(
    audit_log: MasterPasswordAuditLogRepositoryDep,
    limit: int = Query(default=100, ge=1, le=500),
) -> list[MasterPasswordUsageResponse]:
    use_case = ListMasterPasswordUsagesUseCase(audit_log)
    usages = await use_case.execute(limit)
    return [MasterPasswordUsageResponse.from_entity(usage) for usage in usages]
