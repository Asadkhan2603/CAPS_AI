from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_admin_or_teacher_extensions
from app.models.enrollments import enrollment_public
from app.schemas.enrollment import EnrollmentCreate, EnrollmentOut
from app.services.audit import log_audit_event

router = APIRouter()


def _can_manage_class(current_user: dict, class_doc: dict) -> bool:
    if current_user.get("role") == "admin":
        return True
    if current_user.get("role") != "teacher":
        return False
    extensions = current_user.get("extended_roles", [])
    if "year_head" in extensions:
        return True
    if "class_coordinator" in extensions and class_doc.get("class_coordinator_user_id") == str(current_user["_id"]):
        return True
    return False


@router.get("/", response_model=List[EnrollmentOut])
async def list_enrollments(
    class_id: str | None = Query(default=None),
    student_id: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_admin_or_teacher_extensions(["year_head", "class_coordinator"])),
) -> List[EnrollmentOut]:
    query = {}
    if class_id:
        query["class_id"] = class_id
    if student_id:
        query["student_id"] = student_id
    items = await db.enrollments.find(query).skip(skip).limit(limit).to_list(length=limit)
    if current_user.get("role") == "teacher":
        scoped_items = []
        for item in items:
            class_doc = await db.classes.find_one({"_id": parse_object_id(item["class_id"])})
            if class_doc and _can_manage_class(current_user, class_doc):
                scoped_items.append(item)
        items = scoped_items
    return [EnrollmentOut(**enrollment_public(item)) for item in items]


@router.post("/", response_model=EnrollmentOut, status_code=status.HTTP_201_CREATED)
async def create_enrollment(
    payload: EnrollmentCreate,
    current_user=Depends(require_admin_or_teacher_extensions(["year_head", "class_coordinator"])),
) -> EnrollmentOut:
    class_doc = await db.classes.find_one({"_id": parse_object_id(payload.class_id)})
    if not class_doc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Class not found for provided class_id")
    if not _can_manage_class(current_user, class_doc):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to manage this class")

    student = await db.students.find_one({"_id": parse_object_id(payload.student_id)})
    if not student:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student not found for provided student_id")

    if payload.section_id:
        section = await db.sections.find_one({"_id": parse_object_id(payload.section_id)})
        if not section:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Section not found for provided section_id",
            )

    duplicate = await db.enrollments.find_one({"class_id": payload.class_id, "student_id": payload.student_id})
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student already enrolled in class")

    document = {
        "class_id": payload.class_id,
        "student_id": payload.student_id,
        "section_id": payload.section_id,
        "assigned_by_user_id": str(current_user["_id"]),
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.enrollments.insert_one(document)
    created = await db.enrollments.find_one({"_id": result.inserted_id})

    await log_audit_event(
        actor_user_id=str(current_user["_id"]),
        action="enroll_student",
        entity_type="enrollment",
        entity_id=str(result.inserted_id),
        detail=f"Enrolled student {payload.student_id} into class {payload.class_id}",
    )
    return EnrollmentOut(**enrollment_public(created))
