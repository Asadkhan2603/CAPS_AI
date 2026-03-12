from fastapi import APIRouter, Depends, HTTPException, status
from starlette.concurrency import run_in_threadpool

from app.core.security import require_roles
from app.models.ai_chat import ai_chat_public
from app.schemas.ai_chat import AIChatEvaluateRequest, AIChatEvaluateResponse, AIChatThreadOut
from app.services.ai_chat_service import generate_evaluation_chat_reply as default_generate_evaluation_chat_reply
from app.services.ai_chat_workflow import normalize_chat_result, upsert_evaluation_chat_thread
from app.services.ai_runtime import get_ai_runtime_settings
from app.services.audit import log_audit_event

from .ai_common import get_ai_db, resolve_submission, teacher_can_access_assignment_in_scope

router = APIRouter()


@router.post("/evaluate", response_model=AIChatEvaluateResponse)
async def evaluate_with_ai(
    payload: AIChatEvaluateRequest,
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> AIChatEvaluateResponse:
    active_db = get_ai_db()
    actor_id = str(current_user["_id"])
    teacher_id = actor_id if current_user.get("role") == "teacher" else (payload.teacher_id or actor_id)
    student_id = payload.student_id
    exam_id = payload.exam_id

    submission = await resolve_submission(student_id, exam_id, payload.submission_id)
    if current_user.get("role") == "teacher":
        if not await teacher_can_access_assignment_in_scope(actor_id, exam_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this exam")
        if submission and submission.get("student_user_id") != student_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="submission_id does not match student_id")
    elif current_user.get("role") == "admin":
        if submission and submission.get("assignment_id") != exam_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="submission_id does not match exam_id")

    student_answer = payload.student_answer
    if not student_answer and submission:
        student_answer = submission.get("extracted_text") or submission.get("notes") or ""

    # Compatibility seam: tests monkeypatch app.api.v1.endpoints.ai.generate_evaluation_chat_reply.
    from app.api.v1.endpoints import ai as ai_endpoint_module

    chat_generator = getattr(
        ai_endpoint_module,
        "generate_evaluation_chat_reply",
        default_generate_evaluation_chat_reply,
    )
    runtime_settings = await get_ai_runtime_settings()
    ai_result = await run_in_threadpool(
        chat_generator,
        teacher_message=payload.teacher_message,
        question_text=payload.question_text,
        student_answer=student_answer,
        rubric=payload.rubric,
        runtime_settings=runtime_settings,
    )
    ai_response, ai_error, ai_metadata = normalize_chat_result(ai_result)
    updated = await upsert_evaluation_chat_thread(
        database=active_db,
        teacher_id=teacher_id,
        student_id=student_id,
        exam_id=exam_id,
        question_id=payload.question_id,
        teacher_message=payload.teacher_message,
        ai_response=ai_response,
        ai_error=ai_error,
        ai_metadata=ai_metadata,
    )

    await log_audit_event(
        actor_user_id=actor_id,
        action="ai_chat_evaluate",
        entity_type="ai_evaluation_chat",
        entity_id=str(updated["_id"]),
        detail=f"AI chat evaluate exam_id={exam_id} student_id={student_id}",
    )

    return AIChatEvaluateResponse(
        thread=AIChatThreadOut(**ai_chat_public(updated)),
        ai_response=ai_response,
    )


@router.get("/history/{student_id}/{exam_id}", response_model=AIChatThreadOut)
async def get_ai_chat_history(
    student_id: str,
    exam_id: str,
    current_user=Depends(require_roles(["teacher", "admin"])),
) -> AIChatThreadOut:
    active_db = get_ai_db()
    actor_id = str(current_user["_id"])

    if current_user.get("role") == "teacher":
        if not await teacher_can_access_assignment_in_scope(actor_id, exam_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this exam")

    thread = await active_db.ai_evaluation_chats.find_one({"student_id": student_id, "exam_id": exam_id})
    if not thread:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI chat history not found")
    return AIChatThreadOut(**ai_chat_public(thread))
