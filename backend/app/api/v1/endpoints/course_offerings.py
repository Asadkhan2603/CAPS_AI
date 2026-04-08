from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import COURSE_OFFERING_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.course_offerings import course_offering_public
from app.schemas.course_offering import CourseOfferingCreate, CourseOfferingOut, CourseOfferingUpdate
from app.services.academic_hierarchy import validate_section_branch
from app.services.class_slot_read_models import sync_class_slot_read_models_for_offering_query
from app.services.course_offering_read_models import (
    hydrate_course_offerings_from_read_models,
    sync_course_offering_read_model,
)
from app.services.public_ids import persist_public_id, persist_public_id_update

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
    try:
        validate_section_branch(
            section=section,
            batch_id=merged["batch_id"],
            semester_id=merged["semester_id"],
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

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
    items = await hydrate_course_offerings_from_read_models(source_offerings=items, database=db)
    return [CourseOfferingOut(**course_offering_public(item)) for item in items]


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
    persist_public_id(document, kind="course_offering")
    result = await db.course_offerings.insert_one(document)
    created = await db.course_offerings.find_one({"_id": result.inserted_id})
    created = await sync_course_offering_read_model(offering=created, database=db)
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
    persist_public_id_update(current, update_data, kind="course_offering")
    await db.course_offerings.update_one(
        {"_id": offering_obj_id},
        {"$set": {**update_data, "schema_version": COURSE_OFFERING_SCHEMA_VERSION}},
    )
    updated = await db.course_offerings.find_one({"_id": offering_obj_id})
    updated = await sync_course_offering_read_model(offering=updated, database=db)
    await sync_class_slot_read_models_for_offering_query(offering_query={"_id": offering_obj_id}, database=db)
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
    archived = await db.course_offerings.find_one({"_id": offering_obj_id})
    if archived:
        await sync_course_offering_read_model(offering=archived, database=db)
    await sync_class_slot_read_models_for_offering_query(offering_query={"_id": offering_obj_id}, database=db)
    return {"message": "Course offering archived"}
