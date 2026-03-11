from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.semesters import semester_public
from app.schemas.semester_item import SemesterCreate, SemesterOut, SemesterUpdate
from app.services.academic_batching import build_semester_academic_year
from app.services.audit import log_destructive_action_event

router = APIRouter()


@router.get("/", response_model=List[SemesterOut])
async def list_semesters(
    batch_id: str | None = Query(default=None),
    semester_number: int | None = Query(default=None, ge=1, le=12),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[SemesterOut]:
    query: dict[str, Any] = {}
    if batch_id:
        query["batch_id"] = batch_id
    if semester_number is not None:
        query["semester_number"] = semester_number
    if q:
        query["label"] = {"$regex": q, "$options": "i"}
    apply_is_active_filter(query, is_active)
    items = await db.semesters.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [SemesterOut(**semester_public(item)) for item in items]


@router.get("/{semester_id}", response_model=SemesterOut)
async def get_semester(
    semester_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> SemesterOut:
    item = await db.semesters.find_one({"_id": parse_object_id(semester_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    return SemesterOut(**semester_public(item))


@router.post("/", response_model=SemesterOut, status_code=status.HTTP_201_CREATED)
async def create_semester(
    payload: SemesterCreate,
    _current_user=Depends(require_permission("semesters.manage")),
) -> SemesterOut:
    batch = await db.batches.find_one({"_id": parse_object_id(payload.batch_id)})
    if not batch:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch not found for provided batch_id")
    duplicate = await db.semesters.find_one({"batch_id": payload.batch_id, "semester_number": payload.semester_number})
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Semester already exists for this batch")
    academic_year_start, academic_year_end, academic_year_label = build_semester_academic_year(
        batch_start_year=batch.get("start_year"),
        semester_number=payload.semester_number,
    )
    document = {
        "batch_id": payload.batch_id,
        "faculty_id": batch.get("faculty_id"),
        "department_id": batch.get("department_id"),
        "program_id": batch.get("program_id"),
        "specialization_id": batch.get("specialization_id"),
        "semester_number": payload.semester_number,
        "label": payload.label.strip(),
        "academic_year_start": academic_year_start,
        "academic_year_end": academic_year_end,
        "academic_year_label": academic_year_label,
        "university_name": batch.get("university_name"),
        "university_code": batch.get("university_code"),
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.semesters.insert_one(document)
    created = await db.semesters.find_one({"_id": result.inserted_id})
    return SemesterOut(**semester_public(created))


@router.put("/{semester_id}", response_model=SemesterOut)
async def update_semester(
    semester_id: str,
    payload: SemesterUpdate,
    _current_user=Depends(require_permission("semesters.manage")),
) -> SemesterOut:
    semester_obj_id = parse_object_id(semester_id)
    current = await db.semesters.find_one({"_id": semester_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    update_data = payload.model_dump(exclude_none=True)
    if "label" in update_data and update_data["label"]:
        update_data["label"] = update_data["label"].strip()
    target_batch_id = update_data.get("batch_id", current.get("batch_id"))
    target_sem_number = update_data.get("semester_number", current.get("semester_number"))
    batch = None
    if target_batch_id:
        batch = await db.batches.find_one({"_id": parse_object_id(target_batch_id)})
        if not batch:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch not found for provided batch_id")
        academic_year_start, academic_year_end, academic_year_label = build_semester_academic_year(
            batch_start_year=batch.get("start_year"),
            semester_number=int(target_sem_number),
        )
        update_data["faculty_id"] = batch.get("faculty_id")
        update_data["department_id"] = batch.get("department_id")
        update_data["program_id"] = batch.get("program_id")
        update_data["specialization_id"] = batch.get("specialization_id")
        update_data["academic_year_start"] = academic_year_start
        update_data["academic_year_end"] = academic_year_end
        update_data["academic_year_label"] = academic_year_label
        update_data["university_name"] = batch.get("university_name")
        update_data["university_code"] = batch.get("university_code")
    duplicate = await db.semesters.find_one({"batch_id": target_batch_id, "semester_number": target_sem_number})
    if duplicate and duplicate.get("_id") != semester_obj_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Semester already exists for this batch")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = await db.semesters.update_one({"_id": semester_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    updated = await db.semesters.find_one({"_id": semester_obj_id})
    return SemesterOut(**semester_public(updated))


@router.delete("/{semester_id}")
async def delete_semester(
    semester_id: str,
    current_user=Depends(require_permission("semesters.manage")),
) -> dict:
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="semesters.delete",
        entity_type="semester",
        entity_id=semester_id,
        stage="requested",
        detail="Semester delete requested",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    result = await db.semesters.update_one(
        {"_id": parse_object_id(semester_id), "is_active": True},
        build_soft_delete_update(deleted_by=str(current_user.get("_id"))),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Semester not found")
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="semesters.delete",
        entity_type="semester",
        entity_id=semester_id,
        stage="completed",
        detail="Semester archived",
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {"message": "Semester archived"}
