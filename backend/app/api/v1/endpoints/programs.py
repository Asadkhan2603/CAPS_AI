from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import (
    BATCH_SCHEMA_VERSION,
    PROGRAM_SCHEMA_VERSION,
    SEMESTER_SCHEMA_VERSION,
)
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.programs import program_public
from app.schemas.program import ProgramCreate, ProgramOut, ProgramUpdate
from app.services.academic_batching import (
    SEMESTERS_PER_YEAR,
    build_batch_document,
    build_batch_identity,
    build_semester_document,
    resolve_program_academic_context,
)
from app.services.academic_hierarchy import (
    expected_total_semesters,
    validate_duration_and_semesters,
    validate_program_duration,
)
from app.services.master_hierarchy import (
    build_program_business_id,
    coalesce_code,
    coalesce_text,
    ensure_master_hierarchy_change_is_safe,
    normalize_code,
)
from app.services.audit import log_destructive_action_event
from app.services.governance import enforce_review_approval

router = APIRouter()

AUTO_BATCH_START_YEAR = 2022


def _validate_duration_years(duration_years: int) -> int:
    try:
        return validate_program_duration(duration_years)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


def _materialize_program_fields(payload: ProgramCreate | ProgramUpdate) -> tuple[str | None, str | None, str | None]:
    program_name = coalesce_text(getattr(payload, "program_name", None), getattr(payload, "name", None))
    program_code = coalesce_code(getattr(payload, "program_code", None), getattr(payload, "code", None))
    program_id = normalize_code(getattr(payload, "program_id", None))
    return program_name, program_code, program_id


def _normalized_total_semesters(payload: ProgramCreate | ProgramUpdate, duration_years: int) -> int:
    try:
        _, total_semesters = validate_duration_and_semesters(duration_years, getattr(payload, "total_semesters", None))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return total_semesters


async def _safe_find_department(department_id: str | None) -> dict[str, Any] | None:
    if not department_id:
        return None
    try:
        return await db.departments.find_one({"_id": parse_object_id(department_id)})
    except HTTPException:
        return None


async def _safe_find_faculty(faculty_id: str | None) -> dict[str, Any] | None:
    if not faculty_id:
        return None
    try:
        return await db.faculties.find_one({"_id": parse_object_id(str(faculty_id))})
    except HTTPException:
        return None


def _resolve_department_code(department: dict[str, Any] | None) -> str:
    code = str((department or {}).get("department_code") or (department or {}).get("code") or "").strip().upper()
    if code:
        return code
    department_business_id = str((department or {}).get("department_id") or "").strip().upper()
    parts = [part for part in department_business_id.split("-") if part]
    return parts[-1] if parts else "GEN"


def _resolve_faculty_code(*, faculty: dict[str, Any] | None, department: dict[str, Any] | None) -> str:
    code = str((faculty or {}).get("faculty_code") or (faculty or {}).get("code") or "").strip().upper()
    if code:
        return code
    department_business_id = str((department or {}).get("department_id") or "").strip().upper()
    parts = [part for part in department_business_id.split("-") if part]
    return parts[1] if len(parts) >= 3 else "GEN"


async def _program_has_enrolled_semester_students(program_id: str) -> bool:
    cursor = db.classes.find(
        {"program_id": program_id, "semester_id": {"$nin": [None, ""]}},
        {"_id": 1},
    )
    batch_ids: list[str] = []
    async for item in cursor:
        if item.get("_id"):
            batch_ids.append(str(item["_id"]))
        if len(batch_ids) >= 500:
            if await db.enrollments.find_one({"class_id": {"$in": batch_ids}}):
                return True
            batch_ids.clear()
    if batch_ids and await db.enrollments.find_one({"class_id": {"$in": batch_ids}}):
        return True
    return False


async def _sync_program_semesters(program_id: str, total_semesters: int) -> None:
    now = datetime.now(timezone.utc)
    batches = await db.batches.find({"program_id": program_id}).to_list(length=5000)
    for batch in batches:
        batch_id = str(batch["_id"])
        existing = await db.semesters.find(
            {"batch_id": batch_id},
            {"_id": 1, "semester_number": 1, "is_active": 1, "label": 1},
        ).to_list(length=200)
        by_number = {int(item.get("semester_number")): item for item in existing if item.get("semester_number") is not None}

        # Ensure expected semesters exist and are active.
        for semester_number in range(1, total_semesters + 1):
            current = by_number.get(semester_number)
            semester_payload = build_semester_document(
                batch={
                    **batch,
                    "id": batch_id,
                },
                semester_number=semester_number,
                now=now,
            )
            if not current:
                semester_payload["schema_version"] = SEMESTER_SCHEMA_VERSION
                await db.semesters.insert_one(semester_payload)
            else:
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
                current_label = str(current.get("label") or "").strip()
                if not current_label or current_label.startswith("Semester "):
                    update_fields["label"] = semester_payload.get("label")
                if not current.get("is_active", True):
                    update_fields["is_active"] = True
                await db.semesters.update_one(
                    {"_id": current["_id"]},
                    {"$set": update_fields},
                )

        # Archive semesters beyond configured total.
        await db.semesters.update_many(
            {"batch_id": batch_id, "semester_number": {"$gt": total_semesters}, "is_active": True},
            {"$set": {"is_active": False, "updated_at": now, "schema_version": SEMESTER_SCHEMA_VERSION}},
        )


async def _seed_program_batches(program_id: str, duration_years: int) -> int:
    if getattr(db, "batches", None) is None or getattr(db, "semesters", None) is None:
        return 0

    now = datetime.now(timezone.utc)
    current_year = now.year
    program = await db.programs.find_one({"_id": parse_object_id(program_id)})
    if not program:
        return 0
    program_context = await resolve_program_academic_context(db, program=program)
    existing = await db.batches.find(
        {"program_id": program_id, "specialization_id": None},
        {"_id": 1, "start_year": 1},
    ).to_list(length=1000)
    existing_start_years = {int(item.get("start_year")) for item in existing if item.get("start_year") is not None}

    batch_docs: list[dict[str, Any]] = []
    for start_year in range(AUTO_BATCH_START_YEAR, current_year + 1):
        if start_year in existing_start_years:
            continue
        end_year = start_year + duration_years
        name, code = build_batch_identity(
            program_batch_prefix=program_context.get("program_batch_prefix"),
            start_year=start_year,
            end_year=end_year,
            university_code=program_context.get("university_code"),
        )
        batch_docs.append(
            build_batch_document(
                program_context=program_context,
                specialization_id=None,
                name=name,
                code=code,
                start_year=start_year,
                end_year=end_year,
                now=now,
                auto_generated=True,
            )
        )
        batch_docs[-1]["schema_version"] = BATCH_SCHEMA_VERSION

    if not batch_docs:
        return 0

    result = await db.batches.insert_many(batch_docs)
    semester_docs: list[dict[str, Any]] = []
    for batch_id, batch_doc in zip(result.inserted_ids, batch_docs):
        batch_id_str = str(batch_id)
        for semester_number in range(1, duration_years * SEMESTERS_PER_YEAR + 1):
            semester_docs.append(
                build_semester_document(
                    batch={
                        **batch_doc,
                        "id": batch_id_str,
                    },
                    semester_number=semester_number,
                    now=now,
                )
            )
            semester_docs[-1]["schema_version"] = SEMESTER_SCHEMA_VERSION
    if semester_docs:
        await db.semesters.insert_many(semester_docs)
    return len(batch_docs)


async def _sync_auto_generated_batches(program_id: str, duration_years: int) -> None:
    now = datetime.now(timezone.utc)
    program = await db.programs.find_one({"_id": parse_object_id(program_id)})
    if not program:
        return
    program_context = await resolve_program_academic_context(db, program=program)
    rows = await db.batches.find(
        {"program_id": program_id, "specialization_id": None, "auto_generated": True},
        {"_id": 1, "start_year": 1},
    ).to_list(length=1000)

    for row in rows:
        start_year = row.get("start_year")
        if start_year is None:
            continue
        end_year = int(start_year) + duration_years
        name, code = build_batch_identity(
            program_batch_prefix=program_context.get("program_batch_prefix"),
            start_year=int(start_year),
            end_year=end_year,
            university_code=program_context.get("university_code"),
        )
        await db.batches.update_one(
            {"_id": row["_id"]},
            {
                "$set": {
                    "name": name,
                    "code": code,
                    "end_year": end_year,
                    "academic_span_label": f"{int(start_year)}-{end_year}",
                    "faculty_id": program_context.get("faculty_id"),
                    "department_id": program_context.get("department_id"),
                    "university_name": program_context.get("university_name"),
                    "university_code": program_context.get("university_code"),
                    "schema_version": BATCH_SCHEMA_VERSION,
                    "updated_at": now,
                }
            },
        )

    await _seed_program_batches(program_id, duration_years)
    await _sync_program_semesters(program_id, duration_years * SEMESTERS_PER_YEAR)


async def _seed_all_program_batches() -> dict[str, int]:
    programs = await db.programs.find({"is_active": True}, {"_id": 1, "duration_years": 1}).to_list(length=1000)
    program_count = 0
    batch_count = 0
    for program in programs:
        if not program.get("_id"):
            continue
        duration_years = _validate_duration_years(int(program.get("duration_years") or 4))
        existing_rows = await db.batches.find(
            {"program_id": str(program["_id"]), "specialization_id": None, "auto_generated": True},
            {"_id": 1},
        ).to_list(length=1000)
        existing_count = len(existing_rows)
        await _sync_auto_generated_batches(str(program["_id"]), duration_years)
        total_rows = await db.batches.count_documents(
            {"program_id": str(program["_id"]), "specialization_id": None, "auto_generated": True}
        )
        created = max(0, int(total_rows) - existing_count)
        program_count += 1
        batch_count += created
    return {"program_count": program_count, "batch_count": batch_count}


@router.get("/", response_model=List[ProgramOut])
async def list_programs(
    department_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> List[ProgramOut]:
    query: dict[str, Any] = {}
    if department_id:
        query["department_id"] = department_id
    if q:
        query["$or"] = [
            {"program_name": {"$regex": q, "$options": "i"}},
            {"name": {"$regex": q, "$options": "i"}},
            {"program_code": {"$regex": q, "$options": "i"}},
            {"code": {"$regex": q, "$options": "i"}},
            {"program_id": {"$regex": q, "$options": "i"}},
        ]
    apply_is_active_filter(query, is_active)
    items = await db.programs.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [ProgramOut(**program_public(item)) for item in items]


@router.get("/{program_id}", response_model=ProgramOut)
async def get_program(
    program_id: str,
    _current_user=Depends(require_roles(["admin", "teacher"])),
) -> ProgramOut:
    item = await db.programs.find_one({"_id": parse_object_id(program_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    return ProgramOut(**program_public(item))


@router.post("/", response_model=ProgramOut, status_code=status.HTTP_201_CREATED)
async def create_program(
    payload: ProgramCreate,
    _current_user=Depends(require_permission("programs.manage")),
) -> ProgramOut:
    department = await db.departments.find_one({"_id": parse_object_id(payload.department_id)})
    if not department:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department not found for provided department_id")
    duration_years = _validate_duration_years(payload.duration_years)
    total_semesters = _normalized_total_semesters(payload, duration_years)
    program_name, program_code, program_business_id = _materialize_program_fields(payload)
    if not program_name or not program_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program name and code are required")
    faculty = await _safe_find_faculty(department.get("faculty_id"))
    if not program_business_id:
        program_business_id = build_program_business_id(
            faculty_code=_resolve_faculty_code(faculty=faculty, department=department),
            department_code=_resolve_department_code(department),
            program_code=program_code,
        )
    existing = await db.programs.find_one(
        {
            "$or": [
                {"program_id": program_business_id},
                {"department_id": payload.department_id, "program_code": program_code},
                {"department_id": payload.department_id, "code": program_code},
            ]
        }
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program ID or code already exists")
    document = {
        "program_id": program_business_id,
        "program_code": program_code,
        "program_name": program_name,
        "name": program_name,
        "code": program_code,
        "department_id": payload.department_id,
        "duration_years": duration_years,
        "total_semesters": total_semesters,
        "department_master_id": department.get("department_id"),
        "department_name": department.get("department_name") or department.get("name"),
        "department_code": department.get("department_code") or department.get("code"),
        "faculty_master_id": department.get("faculty_master_id"),
        "faculty_code": department.get("faculty_code"),
        "degree_type": coalesce_text(payload.degree_type),
        "description": payload.description,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "schema_version": PROGRAM_SCHEMA_VERSION,
    }
    result = await db.programs.insert_one(document)
    await _seed_program_batches(str(result.inserted_id), duration_years)
    created = await db.programs.find_one({"_id": result.inserted_id})
    return ProgramOut(**program_public(created))


@router.post("/seed-batches")
async def seed_program_batches(
    _current_user=Depends(require_permission("programs.manage")),
) -> dict[str, int | str]:
    summary = await _seed_all_program_batches()
    return {
        "message": "Program batches seeded successfully",
        **summary,
    }


@router.put("/{program_id}", response_model=ProgramOut)
async def update_program(
    program_id: str,
    payload: ProgramUpdate,
    _current_user=Depends(require_permission("programs.manage")),
) -> ProgramOut:
    program_obj_id = parse_object_id(program_id)
    current = await db.programs.find_one({"_id": program_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")

    update_data = payload.model_dump(exclude_none=True)
    if any(key in update_data for key in ("department_master_id", "department_name", "department_code", "faculty_master_id", "faculty_code")) and "department_id" not in update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Program lineage fields are derived from the selected department and cannot be edited independently.",
        )
    department = None
    if "department_id" in update_data:
        if update_data["department_id"] != current.get("department_id"):
            try:
                await ensure_master_hierarchy_change_is_safe(
                    db,
                    entity_kind="program",
                    entity_doc_id=program_id,
                    operation="move to another department",
                )
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
        department = await db.departments.find_one({"_id": parse_object_id(update_data["department_id"])})
        if not department:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department not found for provided department_id")
    else:
        department = await _safe_find_department(current.get("department_id"))
    faculty = await _safe_find_faculty(department.get("faculty_id") if department else None)
    program_name, program_code, program_business_id = _materialize_program_fields(payload)
    if any(key in update_data for key in ("program_name", "name")):
        update_data["program_name"] = program_name
        update_data["name"] = program_name
    if any(key in update_data for key in ("program_code", "code")):
        update_data["program_code"] = program_code
        update_data["code"] = program_code
    if any(key in update_data for key in ("program_id", "program_code", "code", "department_id")) and not update_data.get("program_id"):
        effective_program_code = update_data.get("program_code", current.get("program_code") or current.get("code"))
        update_data["program_id"] = build_program_business_id(
            faculty_code=_resolve_faculty_code(faculty=faculty, department=department),
            department_code=_resolve_department_code(department),
            program_code=effective_program_code,
        )
    next_code = update_data.get("program_code", current.get("program_code") or current.get("code"))
    next_program_id = update_data.get("program_id", current.get("program_id"))
    if next_code or next_program_id:
        duplicate = await db.programs.find_one(
            {
                "_id": {"$ne": program_obj_id},
                "$or": [
                    {"program_id": next_program_id},
                    {"department_id": update_data.get("department_id", current.get("department_id")), "program_code": next_code},
                    {"department_id": update_data.get("department_id", current.get("department_id")), "code": next_code},
                ],
            }
        )
        if duplicate and duplicate.get("_id") != program_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Program ID or code already exists")

    if "duration_years" in update_data:
        new_duration_years = _validate_duration_years(int(update_data["duration_years"]))
        previous_duration_years = int(current.get("duration_years") or 4)
        if new_duration_years != previous_duration_years and await _program_has_enrolled_semester_students(program_id):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot change course duration because students are already enrolled in existing semesters.",
            )
        update_data["duration_years"] = new_duration_years
    effective_duration_years = int(update_data.get("duration_years", current.get("duration_years") or 4))
    if "duration_years" in update_data or "total_semesters" in update_data:
        try:
            _, total_semesters = validate_duration_and_semesters(
                effective_duration_years,
                update_data.get("total_semesters", current.get("total_semesters")),
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
        update_data["total_semesters"] = total_semesters
    if department:
        if any(field in update_data for field in ("department_id", "program_code", "code", "program_id")):
            update_data["department_master_id"] = department.get("department_id")
            update_data["department_name"] = department.get("department_name") or department.get("name")
            update_data["department_code"] = department.get("department_code") or department.get("code")
            update_data["faculty_master_id"] = department.get("faculty_master_id")
            update_data["faculty_code"] = department.get("faculty_code")
    if "degree_type" in update_data and update_data["degree_type"]:
        update_data["degree_type"] = str(update_data["degree_type"]).strip()

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")
    update_data["schema_version"] = PROGRAM_SCHEMA_VERSION
    result = await db.programs.update_one({"_id": program_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    updated = await db.programs.find_one({"_id": program_obj_id})
    if updated and any(field in update_data for field in ("duration_years", "name", "code", "department_id")):
        await _sync_auto_generated_batches(program_id, int(updated.get("duration_years") or 4))
        from app.api.v1.endpoints.specializations import _sync_specialization_batches

        specializations = await db.specializations.find({"program_id": program_id}, {"_id": 1}).to_list(length=1000)
        for specialization in specializations:
            specialization_id = str(specialization.get("_id") or "")
            if specialization_id:
                await _sync_specialization_batches(specialization_id)
    return ProgramOut(**program_public(updated))


@router.delete("/{program_id}")
async def delete_program(
    program_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("programs.manage")),
) -> dict:
    try:
        await ensure_master_hierarchy_change_is_safe(
            db,
            entity_kind="program",
            entity_doc_id=program_id,
            operation="archive",
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="programs.delete",
        entity_type="program",
        entity_id=program_id,
        stage="requested",
        detail="Program delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="programs.delete",
        entity_type="program",
        entity_id=program_id,
    ))
    result = await db.programs.update_one(
        {"_id": parse_object_id(program_id), "is_active": True},
        build_soft_delete_update(
            deleted_by=str(current_user.get("_id")),
            extra_fields={"schema_version": PROGRAM_SCHEMA_VERSION},
        ),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Program not found")
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="programs.delete",
        entity_type="program",
        entity_id=program_id,
        stage="completed",
        detail="Program archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {"message": "Program archived"}
