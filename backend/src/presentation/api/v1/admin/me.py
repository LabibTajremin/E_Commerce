from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel

from src.presentation.dependencies import CurrentAdminDep

router = APIRouter(tags=["admin:me"])


class CurrentAdminResponse(BaseModel):
    user_id: UUID
    tenant_id: UUID
    role: str


@router.get("/me", response_model=CurrentAdminResponse)
async def get_me(current: CurrentAdminDep) -> CurrentAdminResponse:
    return CurrentAdminResponse(
        user_id=current.user_id, tenant_id=current.tenant_id, role=current.role
    )
