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


async def _resolve_student_identifier(student_identifier: str) -> dict | None:
    # Accept either internal student ObjectId or enrollment/roll number.
    student = None
    try:
        student = await db.students.find_one({"_id": parse_object_id(student_identifier)})
    except HTTPException:
        student = None
    if student:
        return student
    return await db.students.find_one({"roll_number": student_identifier})


async def _teacher_manageable_class_ids(current_user: dict, class_id_filter: str | None = None) -> set[str]:
    if current_user.get("role") != "teacher":
        return set()
    teacher_user_id = str(current_user.get("_id"))
    extensions = current_user.get("extended_roles", [])
    if "year_head" in extensions:
        query = {"is_active": True}
        if class_id_filter:
            query["_id"] = parse_object_id(class_id_filter)
        rows = await db.classes.find(query, {"_id": 1}).to_list(length=10000)
        return {str(item.get("_id")) for item in rows if item.get("_id")}
    if "class_coordinator" in extensions:
        query = {"class_coordinator_user_id": teacher_user_id, "is_active": True}
        if class_id_filter:
            query["_id"] = parse_object_id(class_id_filter)
        rows = await db.classes.find(query, {"_id": 1}).to_list(length=1000)
        return {str(item.get("_id")) for item in rows if item.get("_id")}
    return set()


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
        student = await _resolve_student_identifier(student_id)
        if not student:
            return []
        query["student_id"] = {"$in": [str(student["_id"]), student.get("roll_number")]}

    if current_user.get("role") == "teacher":
        manageable_class_ids = await _teacher_manageable_class_ids(current_user, class_id_filter=class_id)
        if not manageable_class_ids:
            return []
        if class_id and class_id not in manageable_class_ids:
            return []
        scoped_query = dict(query)
        if not class_id:
            scoped_query["class_id"] = {"$in": sorted(manageable_class_ids)}
        items = await db.enrollments.find(scoped_query).skip(skip).limit(limit).to_list(length=limit)
    else:
        items = await db.enrollments.find(query).skip(skip).limit(limit).to_list(length=limit)
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

    student = await _resolve_student_identifier(payload.student_id)
    if not student:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student not found for provided student_id")

    canonical_student_id = str(student["_id"])
    candidate_student_ids = [canonical_student_id]
    if student.get("roll_number"):
        candidate_student_ids.append(student["roll_number"])

    duplicate = await db.enrollments.find_one(
        {"class_id": payload.class_id, "student_id": {"$in": candidate_student_ids}}
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Student already enrolled in class")

    document = {
        "class_id": payload.class_id,
        "student_id": canonical_student_id,
        "student_roll_number": student.get("roll_number"),
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
        detail=f"Enrolled student {student.get('roll_number') or canonical_student_id} into class {payload.class_id}",
    )
    return EnrollmentOut(**enrollment_public(created))
