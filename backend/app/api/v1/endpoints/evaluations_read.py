from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.ai_evaluation_runs import ai_evaluation_run_public
from app.models.evaluations import evaluation_public
from app.schemas.evaluation import EvaluationOut
from app.services.evaluation_access_policy import ensure_can_view_evaluation, ensure_teacher_owns_evaluation

from .evaluations_common import get_evaluations_db

router = APIRouter()


@router.get("/", response_model=List[EvaluationOut])
async def list_evaluations(
    submission_id: str | None = Query(default=None),
    student_user_id: str | None = Query(default=None),
    teacher_user_id: str | None = Query(default=None),
    is_finalized: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[EvaluationOut]:
    database = get_evaluations_db()
    query = {}
    if submission_id:
        query["submission_id"] = submission_id
    if student_user_id:
        query["student_user_id"] = student_user_id
    if teacher_user_id:
        query["teacher_user_id"] = teacher_user_id
    if is_finalized is not None:
        query["is_finalized"] = is_finalized

    if current_user.get("role") == "student":
        query["student_user_id"] = str(current_user["_id"])
    if current_user.get("role") == "teacher":
        query["teacher_user_id"] = str(current_user["_id"])

    cursor = database.evaluations.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [EvaluationOut(**evaluation_public(item)) for item in items]


@router.get("/{evaluation_id}", response_model=EvaluationOut)
async def get_evaluation(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> EvaluationOut:
    database = get_evaluations_db()
    item = await database.evaluations.find_one({"_id": parse_object_id(evaluation_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    ensure_can_view_evaluation(current_user, item)
    return EvaluationOut(**evaluation_public(item))


@router.get("/{evaluation_id}/trace")
async def get_evaluation_trace(
    evaluation_id: str,
    limit: int = Query(default=10, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    database = get_evaluations_db()
    item = await database.evaluations.find_one({"_id": parse_object_id(evaluation_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    ensure_teacher_owns_evaluation(current_user, item)

    rows = await database.ai_evaluation_runs.find({"evaluation_id": evaluation_id}).sort("created_at", -1).limit(limit).to_list(length=limit)
    return {
        "evaluation_id": evaluation_id,
        "submission_id": item.get("submission_id"),
        "count": len(rows),
        "items": [ai_evaluation_run_public(row) for row in rows],
    }
