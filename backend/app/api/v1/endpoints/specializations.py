from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import BATCH_SCHEMA_VERSION, SEMESTER_SCHEMA_VERSION, SPECIALIZATION_SCHEMA_VERSION
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.specializations import specialization_public
from app.schemas.specialization import SpecializationCreate, SpecializationOut, SpecializationUpdate
from app.services.academic_batching import (
    build_batch_document,
    build_batch_identity,
    build_semester_document,
    resolve_program_academic_context,
)
from app.services.academic_hierarchy import normalize_program_duration_record
from app.services.master_hierarchy import (
    build_specialization_business_id,
    coalesce_code,
    coalesce_text,
    ensure_master_hierarchy_change_is_safe,
    normalize_code,
)
from app.services.public_ids import persist_public_id, persist_public_id_update
from app.services.audit import log_destructive_action_event
from app.services.batch_read_models import sync_batch_read_models_for_query
from app.services.governance import enforce_review_approval
from app.services.semester_read_models import sync_semester_read_models_for_query
from app.services.section_read_models import sync_section_read_models_for_query

router = APIRouter()

AUTO_BATCH_START_YEAR = 2022


def _normalize_program_duration(program: dict[str, Any]) -> tuple[int, int]:
    return normalize_program_duration_record(program)


def _materialize_specialization_fields(
    payload: SpecializationCreate | SpecializationUpdate,
) -> tuple[str | None, str | None, str | None]:
    specialization_name = coalesce_text(getattr(payload, "specialization_name", None), getattr(payload, "name", None))
    specialization_code = coalesce_code(getattr(payload, "specialization_code", None), getattr(payload, "code", None))
    specialization_id = normalize_code(getattr(payload, "specialization_id", None))
    return specialization_name, specialization_code, specialization_id


def _resolve_program_code(program: dict[str, Any] | None) -> str:
    code = str((program or {}).get("program_code") or (program or {}).get("code") or "").strip().upper()
    if code:
        return code
    program_business_id = str((program or {}).get("program_id") or "").strip().upper()
    parts = [part for part in program_business_id.split("-") if part]
    return "-".join(parts[3:]) if len(parts) >= 4 else "GEN"


def _resolve_department_code(department: dict[str, Any] | None, program: dict[str, Any] | None) -> str:
    code = str((department or {}).get("department_code") or (department or {}).get("code") or "").strip().upper()
    if code:
        return code
    department_business_id = str((department or {}).get("department_id") or (program or {}).get("department_master_id") or "").strip().upper()
    parts = [part for part in department_business_id.split("-") if part]
    return parts[-1] if parts else "GEN"


def _resolve_faculty_code(*, faculty: dict[str, Any] | None, department: dict[str, Any] | None, program: dict[str, Any] | None) -> str:
    code = str((faculty or {}).get("faculty_code") or (faculty or {}).get("code") or "").strip().upper()
    if code:
        return code
    department_business_id = str((department or {}).get("department_id") or (program or {}).get("department_master_id") or "").strip().upper()
    parts = [part for part in department_business_id.split("-") if part]
    return parts[1] if len(parts) >= 3 else "GEN"


def _build_specialization_batch_prefix(program_context: dict[str, Any], specialization: dict[str, Any]) -> str | None:
    program_prefix = str(program_context.get("program_batch_prefix") or "").strip()
    specialization_code = str(
        specialization.get("specialization_code") or specialization.get("code") or ""
    ).strip().upper()
    code_parts = [part for part in [program_prefix, specialization_code] if part]
    return "-".join(code_parts) if code_parts else (program_prefix or specialization_code or None)


async def _seed_specialization_batches(specialization: dict[str, Any], program: dict[str, Any]) -> int:
    now = datetime.now(timezone.utc)
    program_context = await resolve_program_academic_context(db, program=program)
    duration_years, total_semesters = _normalize_program_duration(program)
    specialization_id = str(specialization.get("_id") or specialization.get("id") or "")
    if not specialization_id:
        return 0

    existing = await db.batches.find(
        {"specialization_id": specialization_id},
        {"_id": 1, "start_year": 1},
    ).to_list(length=1000)
    existing_start_years = {int(item.get("start_year")) for item in existing if item.get("start_year") is not None}

    batch_docs: list[dict[str, Any]] = []
    batch_prefix = _build_specialization_batch_prefix(program_context, specialization)
    current_year = now.year
    for start_year in range(AUTO_BATCH_START_YEAR, current_year + 1):
        if start_year in existing_start_years:
            continue
        end_year = start_year + duration_years
        name, code = build_batch_identity(
            program_batch_prefix=batch_prefix,
            start_year=start_year,
            end_year=end_year,
            university_code=program_context.get("university_code"),
        )
        batch_doc = build_batch_document(
            program_context=program_context,
            specialization_id=specialization_id,
            name=name,
            code=code,
            start_year=start_year,
            end_year=end_year,
            now=now,
            auto_generated=True,
        )
        batch_doc["schema_version"] = BATCH_SCHEMA_VERSION
        batch_docs.append(batch_doc)

    if not batch_docs:
        return 0

    result = await db.batches.insert_many(batch_docs)
    semester_docs: list[dict[str, Any]] = []
    for batch_id, batch_doc in zip(result.inserted_ids, batch_docs):
        batch_id_str = str(batch_id)
        for semester_number in range(1, total_semesters + 1):
            semester_doc = build_semester_document(
                batch={
                    **batch_doc,
                    "id": batch_id_str,
                },
                semester_number=semester_number,
                now=now,
            )
            semester_doc["schema_version"] = SEMESTER_SCHEMA_VERSION
            semester_docs.append(semester_doc)
    if semester_docs:
        await db.semesters.insert_many(semester_docs)
    return len(batch_docs)


async def _sync_specialization_batches(specialization_id: str) -> int:
    specialization = await db.specializations.find_one({"_id": parse_object_id(specialization_id)})
    if not specialization:
        return 0
    program = await db.programs.find_one({"_id": parse_object_id(specialization["program_id"])})
    if not program:
        return 0

    now = datetime.now(timezone.utc)
    program_context = await resolve_program_academic_context(db, program=program)
    duration_years, total_semesters = _normalize_program_duration(program)
    batch_prefix = _build_specialization_batch_prefix(program_context, specialization)
    rows = await db.batches.find(
        {"specialization_id": specialization_id, "auto_generated": True},
        {"_id": 1, "start_year": 1},
    ).to_list(length=1000)

    for row in rows:
        start_year = row.get("start_year")
        if start_year is None:
            continue
        end_year = int(start_year) + duration_years
        name, code = build_batch_identity(
            program_batch_prefix=batch_prefix,
            start_year=int(start_year),
            end_year=end_year,
            university_code=program_context.get("university_code"),
        )
        await db.batches.update_one(
            {"_id": row["_id"]},
            {"$set": persist_public_id_update(
                row,
                {
                    "faculty_id": program_context.get("faculty_id"),
                    "department_id": program_context.get("department_id"),
                    "program_id": program_context.get("program_id"),
                    "specialization_id": specialization_id,
                    "name": name,
                    "code": code,
                    "end_year": end_year,
                    "academic_span_label": f"{int(start_year)}-{end_year}",
                    "university_name": program_context.get("university_name"),
                    "university_code": program_context.get("university_code"),
                    "schema_version": BATCH_SCHEMA_VERSION,
                    "updated_at": now,
                },
                kind="batch",
            )},
        )

    await _seed_specialization_batches(specialization, program)

    batches = await db.batches.find({"specialization_id": specialization_id}).to_list(length=5000)
    for batch in batches:
        batch_id = str(batch["_id"])
        existing = await db.semesters.find(
            {"batch_id": batch_id},
            {"_id": 1, "semester_number": 1, "is_active": 1, "label": 1},
        ).to_list(length=200)
        by_number = {
            int(item.get("semester_number")): item
            for item in existing
            if item.get("semester_number") is not None
        }

        for semester_number in range(1, total_semesters + 1):
            semester_payload = build_semester_document(
                batch={
                    **batch,
                    "id": batch_id,
                },
                semester_number=semester_number,
                now=now,
            )
            if semester_number not in by_number:
                semester_payload["schema_version"] = SEMESTER_SCHEMA_VERSION
                await db.semesters.insert_one(semester_payload)
                continue

            current = by_number[semester_number]
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
                "updated_at": now,
            }
            persist_public_id_update(current, update_fields, kind="semester")
            current_label = str(current.get("label") or "").strip()
            if not current_label or current_label.startswith("Semester "):
                update_fields["label"] = semester_payload.get("label")
            if not current.get("is_active", True):
                update_fields["is_active"] = True
            await db.semesters.update_one({"_id": current["_id"]}, {"$set": update_fields})

        await db.semesters.update_many(
            {"batch_id": batch_id, "semester_number": {"$gt": total_semesters}, "is_active": True},
            {"$set": {"is_active": False, "updated_at": now, "schema_version": SEMESTER_SCHEMA_VERSION}},
        )

    return len(rows)


async def _seed_all_specialization_batches() -> dict[str, int]:
    specializations = await db.specializations.find({"is_active": True}, {"_id": 1}).to_list(length=1000)
    specialization_count = 0
    batch_count = 0
    for specialization in specializations:
        specialization_id = str(specialization.get("_id") or "")
        if not specialization_id:
            continue
        existing_count = await db.batches.count_documents({"specialization_id": specialization_id, "auto_generated": True})
        await _sync_specialization_batches(specialization_id)
        total_rows = await db.batches.count_documents({"specialization_id": specialization_id, "auto_generated": True})
        specialization_count += 1
        batch_count += max(0, int(total_rows) - int(existing_count))
    return {"specialization_count": specialization_count, "batch_count": batch_count}


async def _ensure_specialization_reparent_is_safe(specialization_id: str, target_program_id: str) -> None:
    batches = await db.batches.find({"specialization_id": specialization_id}).to_list(length=5000)
    if not batches:
        return

    batch_ids = [str(batch["_id"]) for batch in batches if batch.get("_id")]
    semesters = await db.semesters.find({"batch_id": {"$in": batch_ids}}).to_list(length=5000) if batch_ids else []
    semester_ids = [str(semester["_id"]) for semester in semesters if semester.get("_id")]
    sections = await db.classes.find({"specialization_id": specialization_id}).to_list(length=5000)
    section_ids = [str(section["_id"]) for section in sections if section.get("_id")]

    offering_query: dict[str, Any] = {}
    or_clauses = []
    if batch_ids:
        or_clauses.append({"batch_id": {"$in": batch_ids}})
    if semester_ids:
        or_clauses.append({"semester_id": {"$in": semester_ids}})
    if section_ids:
        or_clauses.append({"section_id": {"$in": section_ids}})
    offerings = (
        await db.course_offerings.find({"$or": or_clauses}).to_list(length=5000)
        if or_clauses and getattr(db, "course_offerings", None) is not None
        else []
    )

    if batches or semesters or sections or offerings:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Specialization cannot be moved to another program while descendant records still exist. "
                f"Found {len(batches)} batches, {len(semesters)} semesters, {len(sections)} sections, "
                f"and {len(offerings)} course offerings under this specialization. "
                "Move or archive descendants before re-parenting the specialization."
            ),
        )


@router.get("/", response_model=List[SpecializationOut])
async def list_specializations(
    program_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[SpecializationOut]:
    query: dict[str, Any] = {}
    if program_id:
        query["program_id"] = program_id
    if q:
        query["$or"] = [
            {"specialization_name": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
            {"specialization_code": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
            {"specialization_id": {"$regex": q, "$options": "i"}},
        ]
    apply_is_active_filter(query, is_active)
    items = await db.specializations.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [SpecializationOut(**specialization_public(item)) for item in items]


@router.post("/seed-batches")
async def seed_specialization_batches(
    _current_user=Depends(require_permission("specializations.manage")),
) -> dict[str, int | str]:
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Specialization batch seeding is disabled in hybrid mode. Create specialization-specific batches manually when needed.",
    )


@router.get("/{specialization_id}", response_model=SpecializationOut)
async def get_specialization(
    specialization_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> SpecializationOut:
    item = await db.specializations.find_one({"_id": parse_object_id(specialization_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialization not found")
    return SpecializationOut(**specialization_public(item))


@router.post("/", response_model=SpecializationOut, status_code=status.HTTP_201_CREATED)
async def create_specialization(
    payload: SpecializationCreate,
    _current_user=Depends(require_permission("specializations.manage")),
) -> SpecializationOut:
    program = await db.programs.find_one({"_id": parse_object_id(payload.program_id)})
    if not program:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
    specialization_name, specialization_code, specialization_id = _materialize_specialization_fields(payload)
    if not specialization_name or not specialization_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization name and code are required")
    department = await db.departments.find_one({"_id": parse_object_id(program["department_id"])}) if program.get("department_id") else None
    faculty = (
        await db.faculties.find_one({"_id": parse_object_id(department["faculty_id"])})
        if department and department.get("faculty_id")
        else None
    )
    if not specialization_id:
        specialization_id = build_specialization_business_id(
            faculty_code=_resolve_faculty_code(faculty=faculty, department=department, program=program),
            department_code=_resolve_department_code(department, program),
            program_code=_resolve_program_code(program),
            specialization_code=specialization_code,
        )
    existing = await db.specializations.find_one(
        {
            "$or": [
                {"specialization_id": specialization_id},
                {"program_id": payload.program_id, "specialization_code": specialization_code},
                {"program_id": payload.program_id, "code": specialization_code},
            ]
        }
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization ID or code already exists")
    document = {
        "specialization_id": specialization_id,
        "specialization_code": specialization_code,
        "specialization_name": specialization_name,
        "name": specialization_name,
        "code": specialization_code,
        "program_id": payload.program_id,
        "program_master_id": program.get("program_id"),
        "program_name": program.get("program_name") or program.get("name"),
        "program_code": program.get("program_code") or program.get("code"),
        "department_master_id": (department or {}).get("department_id"),
        "department_code": (department or {}).get("department_code") or (department or {}).get("code"),
        "faculty_master_id": (department or {}).get("faculty_master_id"),
        "faculty_code": (department or {}).get("faculty_code"),
        "description": payload.description,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "schema_version": SPECIALIZATION_SCHEMA_VERSION,
    }
    persist_public_id(document, kind="specialization")
    result = await db.specializations.insert_one(document)
    created = await db.specializations.find_one({"_id": result.inserted_id})
    return SpecializationOut(**specialization_public(created))


@router.put("/{specialization_id}", response_model=SpecializationOut)
async def update_specialization(
    specialization_id: str,
    payload: SpecializationUpdate,
    _current_user=Depends(require_permission("specializations.manage")),
) -> SpecializationOut:
    specialization_obj_id = parse_object_id(specialization_id)
    update_data = payload.model_dump(exclude_none=True)
    current = await db.specializations.find_one({"_id": specialization_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialization not found")
    if any(key in update_data for key in ("program_master_id", "program_name", "program_code", "department_master_id", "department_code", "faculty_master_id", "faculty_code")) and "program_id" not in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Specialization lineage fields are derived from the selected program and cannot be edited independently.",
        )
    specialization_name, specialization_code, specialization_business_id = _materialize_specialization_fields(payload)
    if any(key in update_data for key in ("specialization_name", "name")):
        update_data["specialization_name"] = specialization_name
        update_data["name"] = specialization_name
    if any(key in update_data for key in ("specialization_code", "code")):
        update_data["specialization_code"] = specialization_code
        update_data["code"] = specialization_code
    if "program_id" in update_data:
        program = await db.programs.find_one({"_id": parse_object_id(update_data["program_id"])})
        if not program:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program not found for provided program_id")
        if update_data["program_id"] != current.get("program_id"):
            await _ensure_specialization_reparent_is_safe(specialization_id, update_data["program_id"])
    else:
        program = await db.programs.find_one({"_id": parse_object_id(current["program_id"])})
    department = await db.departments.find_one({"_id": parse_object_id(program["department_id"])}) if program and program.get("department_id") else None
    faculty = (
        await db.faculties.find_one({"_id": parse_object_id(department["faculty_id"])})
        if department and department.get("faculty_id")
        else None
    )
    if any(key in update_data for key in ("specialization_id", "specialization_code", "code", "program_id")) and not update_data.get("specialization_id"):
        effective_code = update_data.get("specialization_code", current.get("specialization_code") or current.get("code"))
        if effective_code:
            update_data["specialization_id"] = build_specialization_business_id(
                faculty_code=_resolve_faculty_code(faculty=faculty, department=department, program=program),
                department_code=_resolve_department_code(department, program),
                program_code=_resolve_program_code(program),
                specialization_code=effective_code,
            )
    effective_code = update_data.get("specialization_code", current.get("specialization_code") or current.get("code"))
    effective_specialization_id = update_data.get("specialization_id", current.get("specialization_id"))
    duplicate = await db.specializations.find_one(
        {
            "_id": {"$ne": specialization_obj_id},
            "$or": [
                {"specialization_id": effective_specialization_id},
                {"program_id": update_data.get("program_id", current.get("program_id")), "specialization_code": effective_code},
                {"program_id": update_data.get("program_id", current.get("program_id")), "code": effective_code},
            ],
        }
    )
    if duplicate:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Specialization ID or code already exists")
    if program:
        update_data["program_master_id"] = program.get("program_id")
        update_data["program_name"] = program.get("program_name") or program.get("name")
        update_data["program_code"] = program.get("program_code") or program.get("code")
        update_data["department_master_id"] = (department or {}).get("department_id")
        update_data["department_code"] = (department or {}).get("department_code") or (department or {}).get("code")
        update_data["faculty_master_id"] = (department or {}).get("faculty_master_id")
        update_data["faculty_code"] = (department or {}).get("faculty_code")
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    persist_public_id_update(current, update_data, kind="specialization")
    update_data["schema_version"] = SPECIALIZATION_SCHEMA_VERSION
    result = await db.specializations.update_one({"_id": specialization_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialization not found")
    updated = await db.specializations.find_one({"_id": specialization_obj_id})
    await sync_batch_read_models_for_query(query={"specialization_id": specialization_id}, database=db)
    await sync_semester_read_models_for_query(query={"specialization_id": specialization_id}, database=db)
    await sync_section_read_models_for_query(query={"specialization_id": specialization_id}, database=db)
    return SpecializationOut(**specialization_public(updated))


@router.delete("/{specialization_id}")
async def delete_specialization(
    specialization_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("specializations.manage")),
) -> dict:
    try:
        await ensure_master_hierarchy_change_is_safe(
            db,
            entity_kind="specialization",
            entity_doc_id=specialization_id,
            operation="archive",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="specializations.delete",
        entity_type="specialization",
        entity_id=specialization_id,
        stage="requested",
        detail="Specialization delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="specializations.delete",
        entity_type="specialization",
        entity_id=specialization_id,
    ))
    result = await db.specializations.update_one(
        {"_id": parse_object_id(specialization_id), "is_active": True},
        build_soft_delete_update(
            deleted_by=str(current_user.get("_id")),
            extra_fields={"schema_version": SPECIALIZATION_SCHEMA_VERSION},
        ),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Specialization not found")
    await sync_batch_read_models_for_query(query={"specialization_id": specialization_id}, database=db)
    await sync_semester_read_models_for_query(query={"specialization_id": specialization_id}, database=db)
    await sync_section_read_models_for_query(query={"specialization_id": specialization_id}, database=db)
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="specializations.delete",
        entity_type="specialization",
        entity_id=specialization_id,
        stage="completed",
        detail="Specialization archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {"message": "Specialization archived"}
