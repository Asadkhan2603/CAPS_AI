from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.evaluations import evaluation_public
from app.schemas.evaluation import EvaluationAIPreviewOut, EvaluationAIPreviewRequest, EvaluationCreate, EvaluationOut
from app.services.ai_runtime import get_ai_runtime_settings
from app.services.audit import log_audit_event
from app.services.evaluation_access_policy import ensure_teacher_can_evaluate_submission, ensure_teacher_owns_evaluation
from app.services.evaluation_workflow import (
    ai_payload_update_fields,
    build_ai_insight_async,
    build_submission_reuse_ai_payload,
    compute_evaluation_totals,
    persist_ai_trace,
)

from .evaluations_common import get_evaluations_db

router = APIRouter()


@router.post("/ai-preview", response_model=EvaluationAIPreviewOut)
async def preview_evaluation_ai(
    payload: EvaluationAIPreviewRequest,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationAIPreviewOut:
    database = get_evaluations_db()
    submission = await database.submissions.find_one({"_id": parse_object_id(payload.submission_id)})
    if not submission:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission not found for provided submission_id")
    await ensure_teacher_can_evaluate_submission(current_user, submission, database=database)

    payload_data = payload.model_dump()
    internal, total, grade = compute_evaluation_totals(payload_data)
    runtime_settings = await get_ai_runtime_settings()
    ai_payload = build_submission_reuse_ai_payload(submission)
    if ai_payload is None:
        ai_payload = await build_ai_insight_async(
            submission_text=submission.get("extracted_text") or "",
            attendance_percent=payload.attendance_percent,
            internal_total_value=internal,
            grand_total_value=total,
            grade=grade,
            runtime_settings=runtime_settings,
        )

    return EvaluationAIPreviewOut(
        submission_id=payload.submission_id,
        internal_total=internal,
        grand_total=total,
        grade=grade,
        ai_score=ai_payload.get("ai_score"),
        ai_feedback=ai_payload.get("ai_feedback"),
        ai_insight=ai_payload.get("insight"),
    )


@router.post("/", response_model=EvaluationOut, status_code=status.HTTP_201_CREATED)
async def create_evaluation(
    payload: EvaluationCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    database = get_evaluations_db()
    submission = await database.submissions.find_one({"_id": parse_object_id(payload.submission_id)})
    if not submission:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission not found for provided submission_id")
    await ensure_teacher_can_evaluate_submission(current_user, submission, database=database)

    existing = await database.evaluations.find_one({"submission_id": payload.submission_id})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Evaluation already exists for submission")

    payload_data = payload.model_dump()
    internal, total, grade = compute_evaluation_totals(payload_data)
    runtime_settings = await get_ai_runtime_settings()
    ai_payload = build_submission_reuse_ai_payload(submission)
    if ai_payload is None:
        ai_payload = await build_ai_insight_async(
            submission_text=submission.get("extracted_text") or "",
            attendance_percent=payload.attendance_percent,
            internal_total_value=internal,
            grand_total_value=total,
            grade=grade,
            runtime_settings=runtime_settings,
        )
    now = datetime.now(timezone.utc)

    document = {
        "submission_id": payload.submission_id,
        "student_user_id": submission.get("student_user_id"),
        "teacher_user_id": str(current_user["_id"]),
        "attendance_percent": payload.attendance_percent,
        "skill": payload.skill,
        "behavior": payload.behavior,
        "report": payload.report,
        "viva": payload.viva,
        "final_exam": payload.final_exam,
        "internal_total": internal,
        "grand_total": total,
        "grade": grade,
        "remarks": payload.remarks,
        "is_finalized": payload.is_finalized,
        "finalized_at": now if payload.is_finalized else None,
        "finalized_by_user_id": str(current_user["_id"]) if payload.is_finalized else None,
        "created_at": now,
        "updated_at": now,
    }
    document.update(ai_payload_update_fields(ai_payload))

    result = await database.evaluations.insert_one(document)
    created = await database.evaluations.find_one({"_id": result.inserted_id})

    await persist_ai_trace(
        database=database,
        evaluation_id=str(result.inserted_id),
        submission_id=payload.submission_id,
        actor_user_id=str(current_user["_id"]),
        ai_payload=ai_payload,
        totals_payload={"internal_total": internal, "grand_total": total, "grade": grade},
    )

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="create",
        entity_type="evaluation",
        entity_id=str(result.inserted_id),
        detail=f"Created evaluation for submission {payload.submission_id}",
    )

    return EvaluationOut(**evaluation_public(created))


@router.post("/{evaluation_id}/ai-refresh", response_model=EvaluationOut)
async def refresh_evaluation_ai(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    database = get_evaluations_db()
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await database.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    ensure_teacher_owns_evaluation(current_user, item)

    submission = await database.submissions.find_one({"_id": parse_object_id(item.get("submission_id"))})
    if not submission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapped submission not found")

    ai_payload = await build_ai_insight_async(
        submission_text=submission.get("extracted_text") or "",
        attendance_percent=int(item.get("attendance_percent") or 0),
        internal_total_value=float(item.get("internal_total") or 0),
        grand_total_value=float(item.get("grand_total") or 0),
        grade=str(item.get("grade") or "Needs Improvement"),
        runtime_settings=await get_ai_runtime_settings(),
    )

    update_fields = ai_payload_update_fields(ai_payload)
    update_fields["updated_at"] = datetime.now(timezone.utc)
    await database.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {"$set": update_fields},
    )

    await persist_ai_trace(
        database=database,
        evaluation_id=evaluation_id,
        submission_id=item.get("submission_id"),
        actor_user_id=str(current_user["_id"]),
        ai_payload=ai_payload,
        totals_payload={
            "internal_total": item.get("internal_total"),
            "grand_total": item.get("grand_total"),
            "grade": item.get("grade"),
        },
    )

    updated = await database.evaluations.find_one({"_id": evaluation_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="refresh_ai",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail="Refreshed AI insight for evaluation",
    )

    return EvaluationOut(**evaluation_public(updated))
