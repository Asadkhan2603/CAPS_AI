from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.assignments import assignment_public
from app.schemas.assignment import (
    AssignmentCreate,
    AssignmentOut,
    AssignmentPlagiarismToggle,
    AssignmentUpdate,
)
from app.services.audit import log_audit_event

router = APIRouter()


async def _student_visible_class_ids(current_user: dict) -> set[str]:
    user_id = str(current_user["_id"])
    user_email = (current_user.get("email") or "").strip().lower()

    student_profiles = await db.students.find(
        {"$or": [{"email": user_email}, {"user_id": user_id}]}
    ).to_list(length=1000)
    student_ids = [str(item["_id"]) for item in student_profiles]

    class_ids: set[str] = set()
    for profile in student_profiles:
        class_id = profile.get("class_id")
        if class_id:
            class_ids.add(class_id)

    if student_ids:
        enrollments = await db.enrollments.find(
            {"student_id": {"$in": student_ids}}
        ).to_list(length=5000)
        for enrollment in enrollments:
            class_id = enrollment.get("class_id")
            if class_id:
                class_ids.add(class_id)

    return class_ids


@router.get("/", response_model=List[AssignmentOut])
async def list_assignments(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    subject_id: str | None = Query(default=None),
    class_id: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[AssignmentOut]:
    query = {}
    if q:
        query["title"] = {"$regex": q, "$options": "i"}
    if subject_id:
        query["subject_id"] = subject_id
    if class_id:
        query["class_id"] = class_id
    if created_by:
        query["created_by"] = created_by
    if status_filter:
        query["status"] = status_filter
    if current_user.get("role") == "teacher":
        query["created_by"] = str(current_user["_id"])
    if current_user.get("role") == "student":
        class_ids = await _student_visible_class_ids(current_user)
        if not class_ids:
            return []
        query["class_id"] = {"$in": list(class_ids)}

    cursor = db.assignments.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [AssignmentOut(**assignment_public(item)) for item in items]


@router.get("/{assignment_id}", response_model=AssignmentOut)
async def get_assignment(
    assignment_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> AssignmentOut:
    item = await db.assignments.find_one({"_id": parse_object_id(assignment_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if current_user.get("role") == "teacher" and item.get("created_by") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this assignment")
    if current_user.get("role") == "student":
        class_ids = await _student_visible_class_ids(current_user)
        if not class_ids or item.get("class_id") not in class_ids:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this assignment")
    return AssignmentOut(**assignment_public(item))


@router.post("/", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
async def create_assignment(
    payload: AssignmentCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> AssignmentOut:
    document = {
        "title": payload.title.strip(),
        "description": payload.description,
        "subject_id": payload.subject_id,
        "class_id": payload.class_id,
        "due_date": payload.due_date,
        "total_marks": payload.total_marks,
        "status": payload.status,
        "plagiarism_enabled": payload.plagiarism_enabled,
        "created_by": str(current_user.get("_id")),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.assignments.insert_one(document)
    created = await db.assignments.find_one({"_id": result.inserted_id})
    return AssignmentOut(**assignment_public(created))


@router.put("/{assignment_id}", response_model=AssignmentOut)
async def update_assignment(
    assignment_id: str,
    payload: AssignmentUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> AssignmentOut:
    assignment_obj_id = parse_object_id(assignment_id)
    item = await db.assignments.find_one({"_id": assignment_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if current_user.get("role") == "teacher" and item.get("created_by") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this assignment")

    update_data = payload.model_dump(exclude_none=True)
    if "title" in update_data and update_data["title"]:
        update_data["title"] = update_data["title"].strip()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

    result = await db.assignments.update_one(
        {"_id": assignment_obj_id},
        {"$set": update_data},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")

    updated = await db.assignments.find_one({"_id": assignment_obj_id})
    return AssignmentOut(**assignment_public(updated))


@router.patch("/{assignment_id}/plagiarism", response_model=AssignmentOut)
async def toggle_assignment_plagiarism(
    assignment_id: str,
    payload: AssignmentPlagiarismToggle,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> AssignmentOut:
    assignment_obj_id = parse_object_id(assignment_id)
    item = await db.assignments.find_one({"_id": assignment_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if current_user.get("role") == "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin cannot override assignment plagiarism toggle",
        )
    if item.get("created_by") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this assignment")

    await db.assignments.update_one(
        {"_id": assignment_obj_id},
        {"$set": {"plagiarism_enabled": payload.plagiarism_enabled}},
    )
    updated = await db.assignments.find_one({"_id": assignment_obj_id})
    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="toggle_plagiarism",
        entity_type="assignment",
        entity_id=assignment_id,
        detail=f"plagiarism_enabled={payload.plagiarism_enabled}",
    )
    return AssignmentOut(**assignment_public(updated))


@router.delete("/{assignment_id}")
async def delete_assignment(
    assignment_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    assignment_obj_id = parse_object_id(assignment_id)
    item = await db.assignments.find_one({"_id": assignment_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    if current_user.get("role") == "teacher" and item.get("created_by") != str(current_user["_id"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to delete this assignment")

    result = await db.assignments.delete_one({"_id": assignment_obj_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    return {"message": "Assignment deleted"}
