from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_roles
from app.services.ai_runtime_workflow import get_runtime_config_response, update_runtime_config_response
from app.services.ai_semantic_rollout_workflow import (
    activate_semantic_rollout_snapshot_response,
    approve_semantic_rollout_recommendations_response,
    apply_semantic_rollout_recommendations_response,
    get_semantic_rollout_config_response,
    list_semantic_rollout_config_history_response,
    rollback_semantic_rollout_snapshot_response,
    update_semantic_rollout_config_response,
)

from .ai_common import get_ai_db

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


@router.get("/admin/semantic-rollout-config")
async def get_semantic_rollout_config(
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    return await get_semantic_rollout_config_response(database=get_ai_db())


@router.put("/admin/semantic-rollout-config")
async def update_semantic_rollout_config(
    payload: dict[str, Any],
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    return await update_semantic_rollout_config_response(
        payload,
        actor_user_id=str(current_user["_id"]),
        database=get_ai_db(),
    )


@router.post("/admin/semantic-rollout-config/apply-recommendations")
async def apply_semantic_rollout_recommendations(
    payload: dict[str, Any] | None = None,
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    try:
        return await apply_semantic_rollout_recommendations_response(
            payload,
            actor_user_id=str(current_user["_id"]),
            database=get_ai_db(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/admin/semantic-rollout-config/approve-recommendations")
async def approve_semantic_rollout_recommendations(
    payload: dict[str, Any] | None = None,
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    try:
        return await approve_semantic_rollout_recommendations_response(
            payload,
            actor_user_id=str(current_user["_id"]),
            database=get_ai_db(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/admin/semantic-rollout-config/activate")
async def activate_semantic_rollout_snapshot(
    payload: dict[str, Any] | None = None,
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    try:
        return await activate_semantic_rollout_snapshot_response(
            payload,
            actor_user_id=str(current_user["_id"]),
            database=get_ai_db(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/admin/semantic-rollout-config/rollback")
async def rollback_semantic_rollout_snapshot(
    payload: dict[str, Any] | None = None,
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    try:
        return await rollback_semantic_rollout_snapshot_response(
            payload,
            actor_user_id=str(current_user["_id"]),
            database=get_ai_db(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/admin/semantic-rollout-config/history")
async def get_semantic_rollout_config_history(
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin"])),
) -> dict[str, Any]:
    return await list_semantic_rollout_config_history_response(database=get_ai_db(), limit=limit)
