from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.evaluations import evaluation_public
from app.schemas.evaluation import EvaluationOut, EvaluationUpdate
from app.schemas.review_ticket import ReviewTicketDecision
from app.services.ai_runtime import get_ai_runtime_settings
from app.services.audit import log_audit_event
from app.services.evaluation_access_policy import ensure_teacher_owns_evaluation
from app.services.evaluation_workflow import (
    ai_payload_update_fields,
    build_ai_insight_async,
    compute_evaluation_totals,
    persist_ai_trace,
)

from .evaluations_common import get_evaluations_db

router = APIRouter()


@router.put("/{evaluation_id}", response_model=EvaluationOut)
async def update_evaluation(
    evaluation_id: str,
    payload: EvaluationUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    database = get_evaluations_db()
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await database.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    ensure_teacher_owns_evaluation(current_user, item)

    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    if item.get("is_finalized") and current_user.get("role") != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Finalized evaluation can only be modified by admin")

    merged = {
        "attendance_percent": update_data.get("attendance_percent", item.get("attendance_percent", 0)),
        "skill": update_data.get("skill", item.get("skill", 0.0)),
        "behavior": update_data.get("behavior", item.get("behavior", 0.0)),
        "report": update_data.get("report", item.get("report", 0.0)),
        "viva": update_data.get("viva", item.get("viva", 0.0)),
        "final_exam": update_data.get("final_exam", item.get("final_exam", 0)),
    }
    internal, total, grade = compute_evaluation_totals(merged)
    update_data["internal_total"] = internal
    update_data["grand_total"] = total
    update_data["grade"] = grade

    if any(
        key in update_data
        for key in ["attendance_percent", "skill", "behavior", "report", "viva", "final_exam"]
    ):
        submission = await database.submissions.find_one({"_id": parse_object_id(item.get("submission_id"))})
        submission_text = submission.get("extracted_text") if submission else ""
        ai_payload = await build_ai_insight_async(
            submission_text=submission_text or "",
            attendance_percent=int(merged["attendance_percent"]),
            internal_total_value=internal,
            grand_total_value=total,
            grade=grade,
            runtime_settings=await get_ai_runtime_settings(),
        )
        update_data.update(ai_payload_update_fields(ai_payload))
        await persist_ai_trace(
            database=database,
            evaluation_id=evaluation_id,
            submission_id=item.get("submission_id"),
            actor_user_id=str(current_user["_id"]),
            ai_payload=ai_payload,
            totals_payload={"internal_total": internal, "grand_total": total, "grade": grade},
        )

    update_data["updated_at"] = datetime.now(timezone.utc)
    await database.evaluations.update_one({"_id": evaluation_obj_id}, {"$set": update_data})
    updated = await database.evaluations.find_one({"_id": evaluation_obj_id})

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="update",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail="Updated evaluation fields",
    )

    return EvaluationOut(**evaluation_public(updated))


@router.patch("/{evaluation_id}/finalize", response_model=EvaluationOut)
async def finalize_evaluation(
    evaluation_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> EvaluationOut:
    database = get_evaluations_db()
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await database.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")
    ensure_teacher_owns_evaluation(current_user, item)

    await database.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {
            "$set": {
                "is_finalized": True,
                "finalized_at": datetime.now(timezone.utc),
                "finalized_by_user_id": str(current_user["_id"]),
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    updated = await database.evaluations.find_one({"_id": evaluation_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="finalize",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail="Finalized evaluation",
    )
    return EvaluationOut(**evaluation_public(updated))


@router.patch("/{evaluation_id}/override-unfinalize", response_model=EvaluationOut)
async def override_unfinalize_evaluation(
    evaluation_id: str,
    payload: ReviewTicketDecision,
    current_user=Depends(require_roles(["admin"])),
) -> EvaluationOut:
    if not payload.reason or len(payload.reason.strip()) < 5:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reason is required for override")

    database = get_evaluations_db()
    evaluation_obj_id = parse_object_id(evaluation_id)
    item = await database.evaluations.find_one({"_id": evaluation_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Evaluation not found")

    await database.evaluations.update_one(
        {"_id": evaluation_obj_id},
        {
            "$set": {
                "is_finalized": False,
                "updated_at": datetime.now(timezone.utc),
            }
        },
    )
    updated = await database.evaluations.find_one({"_id": evaluation_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="override_unfinalize",
        entity_type="evaluation",
        entity_id=evaluation_id,
        detail=f"Admin override unfinalized evaluation. Reason: {payload.reason.strip()}",
    )
    return EvaluationOut(**evaluation_public(updated))
