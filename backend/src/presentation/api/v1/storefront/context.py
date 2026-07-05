from fastapi import APIRouter, Request

router = APIRouter(tags=["storefront:context"])


@router.get("/context")
async def storefront_context(request: Request) -> dict[str, str]:
    return {"tenant_id": str(request.state.tenant_id)}
