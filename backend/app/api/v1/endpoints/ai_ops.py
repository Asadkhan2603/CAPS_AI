from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.security import require_roles
from app.services.ai_jobs import get_ai_job
from app.services.ai_ops_workflow import build_ai_operations_overview_payload, list_ai_jobs_payload
from app.services.ai_ops_workflow import get_ai_job_detail_payload
from app.services.ai_runtime import get_ai_runtime_settings
from app.services.ai_runtime_workflow import build_provider_mode_payload

from .ai_common import distinct_strings, get_ai_db, serialize_dt, teacher_assignment_scope_ids

router = APIRouter()


@router.get("/ops/overview")
async def get_ai_operations_overview(
    limit: int = Query(default=8, ge=1, le=25),
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> dict[str, Any]:
    active_db = get_ai_db()
    actor_id = str(current_user["_id"])
    role = str(current_user.get("role") or "")

    assignment_scope_ids: list[str] = []
    if role == "teacher":
        assignment_scope_ids = await teacher_assignment_scope_ids(actor_id)
    runtime_settings = await get_ai_runtime_settings()
    return await build_ai_operations_overview_payload(
        database=active_db,
        actor_id=actor_id,
        role=role,
        assignment_scope_ids=assignment_scope_ids,
        limit=limit,
        runtime_settings=runtime_settings,
        provider_payload=build_provider_mode_payload(runtime_settings),
        serialize_dt=serialize_dt,
        distinct_strings=distinct_strings,
    )


@router.get("/jobs")
async def list_ai_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    job_type: str | None = Query(default=None),
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> dict[str, Any]:
    active_db = get_ai_db()
    return await list_ai_jobs_payload(
        database=active_db,
        actor_id=str(current_user["_id"]),
        role=str(current_user.get("role") or ""),
        limit=limit,
        status_filter=status_filter,
        job_type=job_type,
    )


@router.get("/jobs/{job_id}")
async def get_ai_job_detail(
    job_id: str,
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> dict[str, Any]:
    try:
        return await get_ai_job_detail_payload(
            job_id=job_id,
            actor_id=str(current_user["_id"]),
            role=str(current_user.get("role") or ""),
            fetch_ai_job=get_ai_job,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(exc)) from exc
