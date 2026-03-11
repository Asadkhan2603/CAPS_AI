from typing import Any

from fastapi import APIRouter, Depends

from app.core.security import require_roles
from app.services.ai_runtime_workflow import get_runtime_config_response, update_runtime_config_response

router = APIRouter()


@router.get("/admin/runtime-config")
async def get_ai_runtime_config(
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    return await get_runtime_config_response()


@router.put("/admin/runtime-config")
async def update_ai_runtime_config(
    payload: dict[str, Any],
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    return await update_runtime_config_response(
        payload,
        actor_user_id=str(current_user["_id"]),
    )
