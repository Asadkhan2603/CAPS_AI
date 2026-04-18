from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.ai_evaluation_runs import ai_evaluation_run_public
from app.models.evaluations import evaluation_public
from app.schemas.evaluation import EvaluationOut, OfficialMarksheetItemOut, OfficialMarksheetOut
from app.services.evaluation_access_policy import ensure_can_view_evaluation, ensure_teacher_owns_evaluation
from app.services.academic_students import resolve_student_profile_for_user

from .evaluations_common import attach_evaluation_labels, get_evaluations_db

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
    items = await attach_evaluation_labels(items, database=database)
    return [EvaluationOut(**evaluation_public(item)) for item in items]


@router.get("/results/marksheet", response_model=OfficialMarksheetOut)
async def get_official_marksheet(
    student_user_id: str | None = Query(default=None),
    current_user=Depends(require_roles(["admin", "student"])),
) -> OfficialMarksheetOut:
    database = get_evaluations_db()

    target_student_user_id = student_user_id
    if current_user.get("role") == "student":
        target_student_user_id = str(current_user.get("_id"))
    if not target_student_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="student_user_id is required")

    if current_user.get("role") == "student" and target_student_user_id != str(current_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this marksheet")

    student_profile = None
    if current_user.get("role") == "student":
        student_profile = await resolve_student_profile_for_user(current_user, database=database)
    if student_profile is None:
        student_profile = await database.students.find_one({"user_id": target_student_user_id, "is_active": True})

    user_doc = await database.users.find_one({"_id": parse_object_id(target_student_user_id), "is_active": True})
    if not user_doc and student_profile is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Student not found")

    rows = await database.evaluations.find(
        {"student_user_id": target_student_user_id, "result_status": "released"}
    ).sort("released_at", -1).to_list(length=500)

    submission_ids = sorted({row.get("submission_id") for row in rows if row.get("submission_id")})
    submission_map = {}
    assignment_map = {}
    if submission_ids:
        submission_rows = await database.submissions.find(
            {"_id": {"$in": [parse_object_id(value) for value in submission_ids]}},
            {"assignment_id": 1, "original_filename": 1},
        ).to_list(length=len(submission_ids))
        submission_map = {str(item["_id"]): item for item in submission_rows if item.get("_id")}
        assignment_ids = sorted({item.get("assignment_id") for item in submission_rows if item.get("assignment_id")})
        if assignment_ids:
            assignment_rows = await database.assignments.find(
                {"_id": {"$in": [parse_object_id(value) for value in assignment_ids]}},
                {"title": 1},
            ).to_list(length=len(assignment_ids))
            assignment_map = {str(item["_id"]): item for item in assignment_rows if item.get("_id")}

    items = [
        OfficialMarksheetItemOut(
            evaluation_id=str(row["_id"]),
            submission_id=row.get("submission_id"),
            submission_label=(
                assignment_map.get(submission_map.get(row.get("submission_id"), {}).get("assignment_id"), {}).get("title")
                or submission_map.get(row.get("submission_id"), {}).get("original_filename")
            ),
            teacher_user_id=row.get("teacher_user_id"),
            attendance_percent=int(row.get("attendance_percent") or 0),
            internal_total=float(row.get("internal_total") or 0),
            final_exam=int(row.get("final_exam") or 0),
            grand_total=float(row.get("grand_total") or 0),
            grade=row.get("grade") or "Needs Improvement",
            remarks=row.get("remarks"),
            released_at=row.get("released_at"),
            result_version=int(row.get("result_version") or 1),
        )
        for row in rows
    ]
    average_score = round(sum(item.grand_total for item in items) / len(items), 2) if items else 0

    return OfficialMarksheetOut(
        student_user_id=target_student_user_id,
        student_name=(student_profile or {}).get("full_name") or (user_doc or {}).get("full_name"),
        roll_number=(student_profile or {}).get("roll_number"),
        email=(student_profile or {}).get("email") or (user_doc or {}).get("email"),
        generated_at=datetime.now(timezone.utc),
        released_results_count=len(items),
        average_score=average_score,
        items=items,
    )


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
    item = (await attach_evaluation_labels([item], database=database))[0]
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
