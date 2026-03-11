from typing import Any

from fastapi import HTTPException, status

from app.services.access_control import teacher_can_access_assignment


def ensure_teacher_owns_evaluation(current_user: dict[str, Any], evaluation: dict[str, Any]) -> None:
    if current_user.get("role") == "teacher" and evaluation.get("teacher_user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to access this evaluation")


def ensure_can_view_evaluation(current_user: dict[str, Any], evaluation: dict[str, Any]) -> None:
    if current_user.get("role") == "student" and evaluation.get("student_user_id") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this evaluation")
    ensure_teacher_owns_evaluation(current_user, evaluation)


async def ensure_teacher_can_evaluate_submission(
    current_user: dict[str, Any],
    submission: dict[str, Any],
    *,
    database: Any,
) -> None:
    if current_user.get("role") != "teacher":
        return
    assignment_id = submission.get("assignment_id")
    if not assignment_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Submission has no assignment mapping")
    allowed = await teacher_can_access_assignment(
        str(current_user["_id"]),
        assignment_id,
        database=database,
    )
    if not allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to evaluate this submission")
