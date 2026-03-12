from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import COURSE_OFFERING_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.course_offerings import course_offering_public
from app.schemas.course_offering import CourseOfferingCreate, CourseOfferingOut, CourseOfferingUpdate

router = APIRouter()


def _safe_object_ids(values: list[str]) -> list:
    object_ids = []
    for value in values:
        try:
            object_ids.append(parse_object_id(value))
        except HTTPException:
            continue
    return object_ids


async def _ensure_section_write_access(*, current_user: dict, section_id: str) -> None:
    section = await db.classes.find_one({"_id": parse_object_id(section_id), "is_active": True})
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
    if current_user.get("role") == "admin":
        return
    if current_user.get("role") != "teacher":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed")
    if section.get("class_coordinator_user_id") != str(current_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only class coordinator can manage offerings")


async def _validate_payload(payload: CourseOfferingCreate | CourseOfferingUpdate, current: dict | None = None) -> dict:
    target = payload.model_dump(exclude_none=True)
    merged = dict(current or {})
    merged.update(target)

    if not merged.get("section_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="section_id is required")
    if not merged.get("subject_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="subject_id is required")
    if not merged.get("teacher_user_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="teacher_user_id is required")
    if not merged.get("batch_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="batch_id is required")
    if not merged.get("semester_id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="semester_id is required")
    if not merged.get("academic_year"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="academic_year is required")

    section = await db.classes.find_one({"_id": parse_object_id(merged["section_id"]), "is_active": True})
    if not section:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Section not found")
    subject = await db.subjects.find_one({"_id": parse_object_id(merged["subject_id"]), "is_active": True})
    if not subject:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Subject not found")
    teacher = await db.users.find_one({"_id": parse_object_id(merged["teacher_user_id"]), "is_active": True})
    if not teacher or teacher.get("role") not in {"teacher", "admin"}:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Teacher not found")
    batch = await db.batches.find_one({"_id": parse_object_id(merged["batch_id"]), "is_active": True})
    if not batch:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch not found")
    semester = await db.semesters.find_one({"_id": parse_object_id(merged["semester_id"]), "is_active": True})
    if not semester:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Semester not found")
    if semester.get("batch_id") != merged["batch_id"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="semester_id does not belong to provided batch_id")

    if merged.get("group_id"):
        group = await db.groups.find_one({"_id": parse_object_id(merged["group_id"]), "is_active": True})
        if not group:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group not found")
        if group.get("section_id") != merged["section_id"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="group_id does not belong to section_id")

    return merged


@router.get("/", response_model=List[CourseOfferingOut])
async def list_course_offerings(
    section_id: str | None = Query(default=None),
    batch_id: str | None = Query(default=None),
    semester_id: str | None = Query(default=None),
    group_id: str | None = Query(default=None),
    subject_id: str | None = Query(default=None),
    teacher_user_id: str | None = Query(default=None),
    academic_year: str | None = Query(default=None),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> List[CourseOfferingOut]:
    query = {}
    if section_id:
        query["section_id"] = section_id
    if batch_id:
        query["batch_id"] = batch_id
    if semester_id:
        query["semester_id"] = semester_id
    if group_id:
        query["group_id"] = group_id
    if subject_id:
        query["subject_id"] = subject_id
    if teacher_user_id:
        query["teacher_user_id"] = teacher_user_id
    if academic_year:
        query["academic_year"] = academic_year
    if is_active is not None:
        query["is_active"] = is_active

    if current_user.get("role") == "student":
        student = await db.students.find_one({"email": current_user.get("email"), "is_active": True})
        if not student or not student.get("class_id"):
            return []
        query["section_id"] = student.get("class_id")
        query["$or"] = [{"group_id": None}, {"group_id": student.get("group_id")}]

    items = await db.course_offerings.find(query).skip(skip).limit(limit).to_list(length=limit)
    if not items:
        return []

    subject_ids = [item.get("subject_id") for item in items if item.get("subject_id")]
    teacher_ids = [item.get("teacher_user_id") for item in items if item.get("teacher_user_id")]
    section_ids = [item.get("section_id") for item in items if item.get("section_id")]
    group_ids = [item.get("group_id") for item in items if item.get("group_id")]
    semester_ids = [item.get("semester_id") for item in items if item.get("semester_id")]

    subjects = await db.subjects.find({"_id": {"$in": _safe_object_ids(subject_ids)}}, {"name": 1, "code": 1}).to_list(length=5000)
    teachers = await db.users.find({"_id": {"$in": _safe_object_ids(teacher_ids)}}, {"full_name": 1}).to_list(length=5000)
    sections = await db.classes.find({"_id": {"$in": _safe_object_ids(section_ids)}}, {"name": 1}).to_list(length=5000)
    groups = await db.groups.find({"_id": {"$in": _safe_object_ids(group_ids)}}, {"name": 1}).to_list(length=5000)
    semesters = await db.semesters.find({"_id": {"$in": _safe_object_ids(semester_ids)}}, {"label": 1}).to_list(length=5000)

    subject_map = {str(item["_id"]): item for item in subjects if item.get("_id")}
    teacher_map = {str(item["_id"]): item for item in teachers if item.get("_id")}
    section_map = {str(item["_id"]): item for item in sections if item.get("_id")}
    group_map = {str(item["_id"]): item for item in groups if item.get("_id")}
    semester_map = {str(item["_id"]): item for item in semesters if item.get("_id")}

    payloads: List[CourseOfferingOut] = []
    for item in items:
        payload = course_offering_public(item)
        subject = subject_map.get(payload["subject_id"], {})
        teacher = teacher_map.get(payload["teacher_user_id"], {})
        section = section_map.get(payload["section_id"], {})
        group = group_map.get(payload["group_id"], {})
        semester = semester_map.get(payload["semester_id"], {})
        payload["subject_name"] = subject.get("name")
        payload["subject_code"] = subject.get("code")
        payload["teacher_name"] = teacher.get("full_name")
        payload["section_name"] = section.get("name")
        payload["group_name"] = group.get("name")
        payload["semester_label"] = semester.get("label")
        payloads.append(CourseOfferingOut(**payload))

    return payloads


@router.post("/", response_model=CourseOfferingOut, status_code=status.HTTP_201_CREATED)
async def create_course_offering(
    payload: CourseOfferingCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> CourseOfferingOut:
    await _ensure_section_write_access(current_user=current_user, section_id=payload.section_id)
    merged = await _validate_payload(payload)
    duplicate = await db.course_offerings.find_one(
        {
            "subject_id": merged["subject_id"],
            "teacher_user_id": merged["teacher_user_id"],
            "batch_id": merged["batch_id"],
            "semester_id": merged["semester_id"],
            "section_id": merged["section_id"],
            "group_id": merged.get("group_id"),
            "academic_year": merged["academic_year"],
            "offering_type": merged["offering_type"],
            "is_active": True,
        }
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course offering already exists")
    document = {
        **merged,
        "is_active": True,
        "created_by_user_id": str(current_user.get("_id")),
        "created_at": datetime.now(timezone.utc),
        "schema_version": COURSE_OFFERING_SCHEMA_VERSION,
    }
    result = await db.course_offerings.insert_one(document)
    created = await db.course_offerings.find_one({"_id": result.inserted_id})
    return CourseOfferingOut(**course_offering_public(created))


@router.put("/{offering_id}", response_model=CourseOfferingOut)
async def update_course_offering(
    offering_id: str,
    payload: CourseOfferingUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> CourseOfferingOut:
    offering_obj_id = parse_object_id(offering_id)
    current = await db.course_offerings.find_one({"_id": offering_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course offering not found")
    await _ensure_section_write_access(current_user=current_user, section_id=current["section_id"])
    await _validate_payload(payload, current=current)
    update_data = payload.model_dump(exclude_none=True)
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    await db.course_offerings.update_one(
        {"_id": offering_obj_id},
        {"$set": {**update_data, "schema_version": COURSE_OFFERING_SCHEMA_VERSION}},
    )
    updated = await db.course_offerings.find_one({"_id": offering_obj_id})
    return CourseOfferingOut(**course_offering_public(updated))


@router.delete("/{offering_id}")
async def delete_course_offering(
    offering_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict:
    offering_obj_id = parse_object_id(offering_id)
    current = await db.course_offerings.find_one({"_id": offering_obj_id, "is_active": True})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course offering not found")
    await _ensure_section_write_access(current_user=current_user, section_id=current["section_id"])
    await db.course_offerings.update_one(
        {"_id": offering_obj_id},
        {
            "$set": {
                "is_active": False,
                "deleted_at": datetime.now(timezone.utc),
                "schema_version": COURSE_OFFERING_SCHEMA_VERSION,
            }
        },
    )
    return {"message": "Course offering archived"}
