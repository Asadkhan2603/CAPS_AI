from datetime import datetime, timezone
import re
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import BATCH_SCHEMA_VERSION, SEMESTER_SCHEMA_VERSION
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.batches import batch_public
from app.schemas.batch import BatchCreate, BatchOut, BatchUpdate
from app.services.academic_batching import (
    build_batch_document,
    build_semester_document,
    resolve_batch_years,
    resolve_program_academic_context,
)
from app.services.audit import log_destructive_action_event
from app.services.governance import enforce_review_approval

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
    program_context = await resolve_program_academic_context(db, program=program)
    duration_years, total_semesters = _normalize_program_duration(program)
    if payload.specialization_id:
        specialization = await db.specializations.find_one({"_id": parse_object_id(payload.specialization_id)})
        if not specialization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization not found for provided specialization_id")
        if specialization.get("program_id") != payload.program_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="specialization_id does not belong to program_id")

    start_year, end_year = resolve_batch_years(
        start_year=payload.start_year,
        end_year=payload.end_year,
        duration_years=duration_years,
    )

    normalized_code = payload.code.strip()
    existing = await db.batches.find_one(
        {
            "program_id": payload.program_id,
            "specialization_id": payload.specialization_id,
            "code": {"$regex": f"^{re.escape(normalized_code)}$", "$options": "i"},
        }
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch code already exists")
    now = datetime.now(timezone.utc)
    document = build_batch_document(
        program_context=program_context,
        specialization_id=payload.specialization_id,
        name=payload.name.strip(),
        code=normalized_code,
        start_year=start_year,
        end_year=end_year,
        now=now,
        auto_generated=False,
    )
    document["schema_version"] = BATCH_SCHEMA_VERSION
    result = await db.batches.insert_one(document)
    batch_id = str(result.inserted_id)

    semester_docs = [
        build_semester_document(
            batch={
                **document,
                "id": batch_id,
            },
            semester_number=semester_number,
            now=now,
        )
        for semester_number in range(1, total_semesters + 1)
    ]
    for semester_doc in semester_docs:
        semester_doc["schema_version"] = SEMESTER_SCHEMA_VERSION
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
        update_data["code"] = update_data["code"].strip()
        duplicate = await db.batches.find_one(
            {
                "program_id": target_program_id,
                "specialization_id": target_specialization_id,
                "code": {"$regex": f"^{re.escape(update_data['code'])}$", "$options": "i"},
            }
        )
        if duplicate and duplicate.get("_id") != batch_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Batch code already exists")
    if target_program_id:
        program = await db.programs.find_one({"_id": parse_object_id(target_program_id)})
        if not program:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
        duration_years, _ = _normalize_program_duration(program)
        program_context = await resolve_program_academic_context(db, program=program)
    else:
        duration_years = 4
        program_context = {
            "faculty_id": current.get("faculty_id"),
            "department_id": current.get("department_id"),
            "program_id": target_program_id,
            "university_name": current.get("university_name"),
            "university_code": current.get("university_code"),
        }
    if target_specialization_id:
        specialization = await db.specializations.find_one({"_id": parse_object_id(target_specialization_id)})
        if not specialization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization not found for provided specialization_id")
        if specialization.get("program_id") != target_program_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="specialization_id does not belong to program_id")

    resolved_start_year, resolved_end_year = resolve_batch_years(
        start_year=update_data.get("start_year", current.get("start_year")),
        end_year=update_data.get("end_year", current.get("end_year")),
        duration_years=duration_years,
    )
    if "start_year" in update_data or "end_year" in update_data or "program_id" in update_data:
        update_data["start_year"] = resolved_start_year
        update_data["end_year"] = resolved_end_year
        update_data["academic_span_label"] = None if resolved_start_year is None or resolved_end_year is None else f"{resolved_start_year}-{resolved_end_year}"
    if "program_id" in update_data or "specialization_id" in update_data or "start_year" in update_data or "end_year" in update_data:
        update_data["faculty_id"] = program_context.get("faculty_id")
        update_data["department_id"] = program_context.get("department_id")
        update_data["university_name"] = program_context.get("university_name")
        update_data["university_code"] = program_context.get("university_code")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    update_data["schema_version"] = BATCH_SCHEMA_VERSION
    result = await db.batches.update_one({"_id": batch_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
    updated = await db.batches.find_one({"_id": batch_obj_id})
    if updated:
        semesters = await db.semesters.find({"batch_id": batch_id}).to_list(length=200)
        for semester in semesters:
            semester_number = semester.get("semester_number")
            if semester_number is None:
                continue
            semester_payload = build_semester_document(
                batch={
                    **updated,
                    "id": batch_id,
                },
                semester_number=int(semester_number),
                now=datetime.now(timezone.utc),
            )
            update_fields = {
                "faculty_id": semester_payload.get("faculty_id"),
                "department_id": semester_payload.get("department_id"),
                "program_id": semester_payload.get("program_id"),
                "specialization_id": semester_payload.get("specialization_id"),
                "academic_year_start": semester_payload.get("academic_year_start"),
                "academic_year_end": semester_payload.get("academic_year_end"),
                "academic_year_label": semester_payload.get("academic_year_label"),
                "university_name": semester_payload.get("university_name"),
                "university_code": semester_payload.get("university_code"),
                "schema_version": SEMESTER_SCHEMA_VERSION,
            }
            current_label = str(semester.get("label") or "").strip()
            if not current_label or current_label.startswith("Semester "):
                update_fields["label"] = semester_payload.get("label")
            await db.semesters.update_one(
                {"_id": semester["_id"]},
                build_state_update(update_fields),
            )
    return BatchOut(**batch_public(updated))


@router.delete("/{batch_id}")
async def delete_batch(
    batch_id: str,
    review_id: str | None = Query(default=None),
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
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="batches.delete",
        entity_type="batch",
        entity_id=batch_id,
    ))
    result = await db.batches.update_one(
        {"_id": parse_object_id(batch_id), "is_active": True},
        build_soft_delete_update(
            deleted_by=str(current_user.get("_id")),
            extra_fields={"schema_version": BATCH_SCHEMA_VERSION},
        ),
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
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {"message": "Batch archived"}
