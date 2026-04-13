from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import EXAM_SCHEMA_VERSION
from app.core.security import require_roles
from app.models.exams import exam_public
from app.schemas.exam import ExamCreate, ExamOut, ExamUpdate
from app.services.academic_students import resolve_student_academic_context_for_user
from app.services.public_ids import persist_public_id, persist_public_id_update

router = APIRouter()


async def _validate_exam_relations(payload: dict[str, Any]) -> None:
    lookups = (
        ("subject_id", "subjects", "Subject"),
        ("batch_id", "batches", "Batch"),
        ("semester_id", "semesters", "Semester"),
        ("section_id", "classes", "Section"),
        ("assignment_id", "assignments", "Assignment"),
    )
    for field_name, collection_name, label in lookups:
        field_value = payload.get(field_name)
        if not field_value:
            continue
        collection = getattr(db, collection_name, None)
        if collection is None:
            continue
        row = await collection.find_one({"_id": parse_object_id(field_value)})
        if not row:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{label} not found for provided {field_name}")


@router.get("/", response_model=list[ExamOut])
async def list_exams(
    subject_id: str | None = Query(default=None),
    batch_id: str | None = Query(default=None),
    semester_id: str | None = Query(default=None),
    section_id: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> list[ExamOut]:
    query: dict[str, Any] = {"is_active": True}
    if subject_id:
        query["subject_id"] = subject_id
    if batch_id:
        query["batch_id"] = batch_id
    if semester_id:
        query["semester_id"] = semester_id
    if section_id:
        query["section_id"] = section_id
    if status_filter:
        query["status"] = status_filter

    if current_user.get("role") == "teacher":
        query["$or"] = [
            {"teacher_user_id": str(current_user.get("_id"))},
            {"created_by": str(current_user.get("_id"))},
        ]
    if current_user.get("role") == "student":
        context = await resolve_student_academic_context_for_user(current_user, database=db, raise_not_found=True)
        query["section_id"] = context.get("canonical_class_id")

    rows = await db.exams.find(query).sort("scheduled_for", 1).skip(skip).limit(limit).to_list(length=limit)
    return [ExamOut(**exam_public(row)) for row in rows]


@router.get("/{exam_id}", response_model=ExamOut)
async def get_exam(
    exam_id: str,
    current_user=Depends(require_roles(["admin", "teacher", "student"])),
) -> ExamOut:
    item = await db.exams.find_one({"_id": parse_object_id(exam_id), "is_active": True})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if current_user.get("role") == "teacher" and item.get("teacher_user_id") not in {str(current_user.get("_id")), None} and item.get("created_by") != str(current_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this exam")
    if current_user.get("role") == "student":
        context = await resolve_student_academic_context_for_user(current_user, database=db, raise_not_found=True)
        if item.get("section_id") != context.get("canonical_class_id"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to view this exam")
    return ExamOut(**exam_public(item))


@router.post("/", response_model=ExamOut, status_code=status.HTTP_201_CREATED)
async def create_exam(
    payload: ExamCreate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> ExamOut:
    document = payload.model_dump()
    await _validate_exam_relations(document)
    document.update(
        {
            "title": payload.title.strip(),
            "code": (payload.code or "").strip() or None,
            "room_code": (payload.room_code or "").strip() or None,
            "created_by": str(current_user.get("_id") or ""),
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "schema_version": EXAM_SCHEMA_VERSION,
        }
    )
    if current_user.get("role") == "teacher" and not document.get("teacher_user_id"):
        document["teacher_user_id"] = str(current_user.get("_id"))
    persist_public_id(document, kind="exam")
    result = await db.exams.insert_one(document)
    created = await db.exams.find_one({"_id": result.inserted_id})
    return ExamOut(**exam_public(created))


@router.put("/{exam_id}", response_model=ExamOut)
async def update_exam(
    exam_id: str,
    payload: ExamUpdate,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> ExamOut:
    exam_obj_id = parse_object_id(exam_id)
    item = await db.exams.find_one({"_id": exam_obj_id, "is_active": True})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if current_user.get("role") == "teacher" and item.get("teacher_user_id") not in {str(current_user.get("_id")), None} and item.get("created_by") != str(current_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to update this exam")

    update_data = payload.model_dump(exclude_none=True)
    if "title" in update_data and update_data["title"]:
        update_data["title"] = update_data["title"].strip()
    if "code" in update_data:
        update_data["code"] = (update_data["code"] or "").strip() or None
    if "room_code" in update_data:
        update_data["room_code"] = (update_data["room_code"] or "").strip() or None
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    await _validate_exam_relations({**item, **update_data})
    persist_public_id_update(item, update_data, kind="exam")
    update_data["updated_at"] = datetime.now(timezone.utc)
    update_data["schema_version"] = EXAM_SCHEMA_VERSION
    await db.exams.update_one({"_id": exam_obj_id}, {"$set": update_data})
    updated = await db.exams.find_one({"_id": exam_obj_id})
    return ExamOut(**exam_public(updated))


@router.delete("/{exam_id}")
async def delete_exam(
    exam_id: str,
    current_user=Depends(require_roles(["admin", "teacher"])),
) -> dict[str, str]:
    exam_obj_id = parse_object_id(exam_id)
    item = await db.exams.find_one({"_id": exam_obj_id, "is_active": True})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam not found")
    if current_user.get("role") == "teacher" and item.get("teacher_user_id") not in {str(current_user.get("_id")), None} and item.get("created_by") != str(current_user.get("_id")):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to archive this exam")
    await db.exams.update_one(
        {"_id": exam_obj_id},
        {
            "$set": {
                "is_active": False,
                "updated_at": datetime.now(timezone.utc),
                "schema_version": EXAM_SCHEMA_VERSION,
            }
        },
    )
    return {"message": "Exam archived"}
