from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.batches import batch_public
from app.schemas.batch import BatchCreate, BatchOut, BatchUpdate
from app.services.audit import log_destructive_action_event

router = APIRouter()


def _normalize_program_duration(program: dict[str, Any]) -> tuple[int, int]:
    try:
        raw_duration_years = program.get("duration_years")
        if raw_duration_years is None:
            raise TypeError
        duration_years = int(raw_duration_years)
    except (TypeError, ValueError):
        duration_years = 4
    duration_years = max(3, min(5, duration_years))

    try:
        raw_total_semesters = program.get("total_semesters")
        if raw_total_semesters is None:
            raise TypeError
        total_semesters = int(raw_total_semesters)
    except (TypeError, ValueError):
        total_semesters = duration_years * 2
    if total_semesters <= 0:
        total_semesters = duration_years * 2
    return duration_years, total_semesters


def _resolve_batch_years(*, start_year: int | None, end_year: int | None, duration_years: int) -> tuple[int | None, int | None]:
    if start_year is not None and end_year is None:
        end_year = start_year + duration_years
    elif end_year is not None and start_year is None:
        start_year = end_year - duration_years

    if start_year is not None and end_year is not None:
        if end_year < start_year:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="End year cannot be earlier than start year")
        expected_end_year = start_year + duration_years
        if end_year != expected_end_year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Batch span must match program duration of {duration_years} years.",
            )

    return start_year, end_year


@router.get("/", response_model=List[BatchOut])
async def list_batches(
    program_id: str | None = Query(default=None),
    specialization_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[BatchOut]:
    query: dict[str, Any] = {}
    if program_id:
        query["program_id"] = program_id
    if specialization_id:
        query["specialization_id"] = specialization_id
    if q:
        query["$or"] = [
            {"name": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
        ]
    apply_is_active_filter(query, is_active)
    items = await db.batches.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [BatchOut(**batch_public(item)) for item in items]


@router.get("/{batch_id}", response_model=BatchOut)
async def get_batch(
    batch_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> BatchOut:
    item = await db.batches.find_one({"_id": parse_object_id(batch_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    return BatchOut(**batch_public(item))


@router.post("/", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
async def create_batch(
    payload: BatchCreate,
    _current_user=Depends(require_permission("batches.manage")),
) -> BatchOut:
    program = await db.programs.find_one({"_id": parse_object_id(payload.program_id)})
    if not program:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
    duration_years, total_semesters = _normalize_program_duration(program)
    if payload.specialization_id:
        specialization = await db.specializations.find_one({"_id": parse_object_id(payload.specialization_id)})
        if not specialization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization not found for provided specialization_id")
        if specialization.get("program_id") != payload.program_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="specialization_id does not belong to program_id")

    start_year, end_year = _resolve_batch_years(
        start_year=payload.start_year,
        end_year=payload.end_year,
        duration_years=duration_years,
    )

    normalized_code = payload.code.strip().upper()
    existing = await db.batches.find_one(
        {
            "program_id": payload.program_id,
            "specialization_id": payload.specialization_id,
            "code": normalized_code,
        }
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch code already exists")
    document = {
        "program_id": payload.program_id,
        "specialization_id": payload.specialization_id,
        "name": payload.name.strip(),
        "code": normalized_code,
        "start_year": start_year,
        "end_year": end_year,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.batches.insert_one(document)
    batch_id = str(result.inserted_id)

    semester_docs = [
        {
            "batch_id": batch_id,
            "semester_number": semester_number,
            "label": f"Semester {semester_number}",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        for semester_number in range(1, total_semesters + 1)
    ]
    if semester_docs:
        await db.semesters.insert_many(semester_docs)

    created = await db.batches.find_one({"_id": result.inserted_id})
    return BatchOut(**batch_public(created))


@router.put("/{batch_id}", response_model=BatchOut)
async def update_batch(
    batch_id: str,
    payload: BatchUpdate,
    _current_user=Depends(require_permission("batches.manage")),
) -> BatchOut:
    batch_obj_id = parse_object_id(batch_id)
    current = await db.batches.find_one({"_id": batch_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    update_data = payload.model_dump(exclude_none=True)
    target_program_id = update_data.get("program_id", current.get("program_id"))
    target_specialization_id = update_data.get("specialization_id", current.get("specialization_id"))
    if "name" in update_data and update_data["name"]:
        update_data["name"] = update_data["name"].strip()
    if "code" in update_data and update_data["code"]:
        update_data["code"] = update_data["code"].strip().upper()
        duplicate = await db.batches.find_one(
            {
                "program_id": target_program_id,
                "specialization_id": target_specialization_id,
                "code": update_data["code"],
            }
        )
        if duplicate and duplicate.get("_id") != batch_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch code already exists")
    if target_program_id:
        program = await db.programs.find_one({"_id": parse_object_id(target_program_id)})
        if not program:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
        duration_years, _ = _normalize_program_duration(program)
    else:
        duration_years = 4
    if target_specialization_id:
        specialization = await db.specializations.find_one({"_id": parse_object_id(target_specialization_id)})
        if not specialization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization not found for provided specialization_id")
        if specialization.get("program_id") != target_program_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="specialization_id does not belong to program_id")

    resolved_start_year, resolved_end_year = _resolve_batch_years(
        start_year=update_data.get("start_year", current.get("start_year")),
        end_year=update_data.get("end_year", current.get("end_year")),
        duration_years=duration_years,
    )
    if "start_year" in update_data or "end_year" in update_data or "program_id" in update_data:
        update_data["start_year"] = resolved_start_year
        update_data["end_year"] = resolved_end_year
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    result = await db.batches.update_one({"_id": batch_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    updated = await db.batches.find_one({"_id": batch_obj_id})
    return BatchOut(**batch_public(updated))


@router.delete("/{batch_id}")
async def delete_batch(
    batch_id: str,
    current_user=Depends(require_permission("batches.manage")),
) -> dict:
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="batches.delete",
        entity_type="batch",
        entity_id=batch_id,
        stage="requested",
        detail="Batch delete requested",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    result = await db.batches.update_one(
        {"_id": parse_object_id(batch_id), "is_active": True},
        build_soft_delete_update(deleted_by=str(current_user.get("_id"))),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="batches.delete",
        entity_type="batch",
        entity_id=batch_id,
        stage="completed",
        detail="Batch archived",
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {"message": "Batch archived"}
