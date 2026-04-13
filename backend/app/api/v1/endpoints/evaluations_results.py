from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.schemas.evaluation import (
    GradingPolicyOut,
    GradingPolicyUpdate,
    SemesterResultCorrectionRequest,
    SemesterResultOut,
    SemesterResultReopenRequest,
    TranscriptOut,
)
from app.services.audit import log_audit_event
from app.services.official_results import (
    build_transcript,
    publish_semester_result,
    request_semester_result_correction,
)
from app.services.grading_policy import get_grading_policy, set_grading_policy

from .evaluations_common import get_evaluations_db

router = APIRouter()


def _semester_result_public(document: dict) -> SemesterResultOut:
    return SemesterResultOut(
        id=str(document["_id"]),
        student_user_id=document.get("student_user_id"),
        student_name=document.get("student_name"),
        roll_number=document.get("roll_number"),
        semester_id=document.get("semester_id"),
        semester_label=document.get("semester_label"),
        semester_number=document.get("semester_number"),
        class_id=document.get("class_id"),
        class_name=document.get("class_name"),
        batch_id=document.get("batch_id"),
        status=document.get("status", "released"),
        result_version=int(document.get("result_version") or 1),
        released_at=document.get("released_at"),
        released_by_user_id=document.get("released_by_user_id"),
        correction_requested_at=document.get("correction_requested_at"),
        correction_requested_by_user_id=document.get("correction_requested_by_user_id"),
        correction_reason=document.get("correction_reason"),
        reopened_at=document.get("reopened_at"),
        reopened_by_user_id=document.get("reopened_by_user_id"),
        reopen_reason=document.get("reopen_reason"),
        result_count=int(document.get("result_count") or 0),
        average_score=float(document.get("average_score") or 0),
        gpa=float(document.get("gpa") or 0),
        items=list(document.get("items") or []),
        created_at=document.get("created_at"),
        updated_at=document.get("updated_at"),
        schema_version=int(document.get("schema_version") or 1),
    )


@router.get("/results/summary", response_model=list[SemesterResultOut])
async def list_semester_results(
    student_user_id: str | None = Query(default=None),
    current_user=Depends(require_roles(["admin", "student"])),
) -> list[SemesterResultOut]:
    database = get_evaluations_db()
    target_student_user_id = student_user_id or str(current_user.get("_id"))
    if current_user.get("role") == "student":
        target_student_user_id = str(current_user.get("_id"))

    rows = await database.semester_results.find(
        {"student_user_id": target_student_user_id, "is_active": True}
    ).sort("semester_number", 1).to_list(length=100)
    return [_semester_result_public(row) for row in rows]


@router.post("/results/publish-from-evaluation/{evaluation_id}", response_model=SemesterResultOut)
async def publish_semester_result_from_evaluation(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> SemesterResultOut:
    database = get_evaluations_db()
    evaluation = await database.evaluations.find_one({"_id": parse_object_id(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    if evaluation.get("result_status") != "released":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Release the evaluation result before publishing a semester result")

    try:
        result_doc = await publish_semester_result(
            trigger_evaluation=evaluation,
            actor_user_id=str(current_user.get("_id") or ""),
            database=database,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    await log_audit_event(
        actor_user_id=str(current_user.get("_id") or ""),
        action="publish_semester_result",
        entity_type="semester_result",
        entity_id=str(result_doc.get("_id") or ""),
        detail=f"Published semester result version {int(result_doc.get('result_version') or 1)}",
    )
    return _semester_result_public(result_doc)


@router.post("/results/request-correction-from-evaluation/{evaluation_id}", response_model=SemesterResultOut)
async def request_semester_result_correction_from_evaluation(
    evaluation_id: str,
    payload: SemesterResultCorrectionRequest,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> SemesterResultOut:
    database = get_evaluations_db()
    evaluation = await database.evaluations.find_one({"_id": parse_object_id(evaluation_id)})
    if not evaluation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    result_doc = await request_semester_result_correction(
        trigger_evaluation=evaluation,
        actor_user_id=str(current_user.get("_id") or ""),
        reason=payload.reason,
        database=database,
    )
    if not result_doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester result not found for this evaluation")

    await log_audit_event(
        actor_user_id=str(current_user.get("_id") or ""),
        action="request_semester_result_correction",
        entity_type="semester_result",
        entity_id=str(result_doc.get("_id") or ""),
        detail=f"Requested semester result correction. Reason: {payload.reason.strip()}",
    )
    return _semester_result_public(result_doc)


@router.post("/results/{result_id}/reopen", response_model=SemesterResultOut)
async def reopen_semester_result(
    result_id: str,
    payload: SemesterResultReopenRequest,
    current_user=Depends(require_roles(["admin"])),
) -> SemesterResultOut:
    database = get_evaluations_db()
    result_obj_id = parse_object_id(result_id)
    item = await database.semester_results.find_one({"_id": result_obj_id, "is_active": True})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester result not found")

    await database.semester_results.update_one(
        {"_id": result_obj_id},
        {
            "$set": {
                "status": "reopened",
                "reopened_at": datetime.now(timezone.utc),
                "reopened_by_user_id": str(current_user.get("_id") or ""),
                "reopen_reason": payload.reason.strip(),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    updated = await database.semester_results.find_one({"_id": result_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user.get("_id") or ""),
        action="reopen_semester_result",
        entity_type="semester_result",
        entity_id=result_id,
        detail=f"Reopened semester result. Reason: {payload.reason.strip()}",
    )
    return _semester_result_public(updated)


@router.get("/results/transcript", response_model=TranscriptOut)
async def get_transcript(
    student_user_id: str | None = Query(default=None),
    current_user=Depends(require_roles(["admin", "student"])),
    ) -> TranscriptOut:
    database = get_evaluations_db()
    target_student_user_id = student_user_id or str(current_user.get("_id"))
    if current_user.get("role") == "student":
        target_student_user_id = str(current_user.get("_id"))
    payload = await build_transcript(student_user_id=target_student_user_id, database=database)
    return TranscriptOut(**payload)


@router.get("/results/grading-policy", response_model=GradingPolicyOut)
async def get_result_grading_policy(
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> GradingPolicyOut:
    database = get_evaluations_db()
    return GradingPolicyOut(**(await get_grading_policy(database=database)))


@router.patch("/results/grading-policy", response_model=GradingPolicyOut)
async def update_result_grading_policy(
    payload: GradingPolicyUpdate,
    current_user=Depends(require_roles(["admin"])),
) -> GradingPolicyOut:
    database = get_evaluations_db()
    updated = await set_grading_policy(payload=payload.model_dump(exclude_none=True), database=database)
    await log_audit_event(
        actor_user_id=str(current_user.get("_id") or ""),
        action="update_result_grading_policy",
        entity_type="grading_policy",
        entity_id="academic_grading_policy",
        detail="Updated academic grading policy for official results and transcript calculations",
    )
    return GradingPolicyOut(**updated)
