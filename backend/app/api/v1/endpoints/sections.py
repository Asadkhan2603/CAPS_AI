from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLASS_SCHEMA_VERSION, GROUP_SCHEMA_VERSION
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.sections import section_public
from app.schemas.section import (
    SectionCreate,
    SectionDashboardResponse,
    SectionLockRequest,
    SectionOperationalSummaryOut,
    SectionOut,
    SectionUpdate,
)
from app.services.academic_hierarchy import validate_batch_specialization_scope
from app.services.audit import log_audit_event, log_destructive_action_event
from app.services.governance import enforce_review_approval
from app.services.section_read_models import (
    get_section_read_model,
    hydrate_sections_from_read_models,
    sync_section_read_model,
)
from app.services.rbac import build_batch_scope_filter, is_document_in_batch_scope, merge_query_with_scope_filter
from app.services.section_mapping import (
    can_lock_or_unlock_section,
    get_section_or_404,
    coordinator_scope_class_id,
    section_mapping_lock_state,
    sync_section_coordinator_assignment,
    validate_section_coordinator_user,
    is_section_coordinator,
)
from app.services.public_ids import persist_public_id, persist_public_id_update
from app.services.attendance_summary import build_attendance_section_summary
from app.api.v1.endpoints.timetables import _compute_sync_snapshot

router = APIRouter()
AUTO_SECTION_GROUP_SLOTS = ("A", "B")


def _build_auto_group_identity(section_name: str, slot: str) -> tuple[str, str]:
    normalized_section_name = str(section_name or "").strip()
    group_name = f"Group {slot}"
    group_code = f"{normalized_section_name}-{slot}".upper()
    return group_name, group_code


async def _apply_admin_scope_to_query(current_user: dict[str, Any], query: dict[str, Any]) -> dict[str, Any]:
    if current_user.get("role") != "admin":
        return query
    scope_filter = await build_batch_scope_filter(
        current_user,
        department_field="department_id",
        batch_field="batch_id",
        database=db,
    )
    return merge_query_with_scope_filter(query, scope_filter)


async def _ensure_admin_can_access_section(current_user: dict[str, Any], section: dict[str, Any] | None) -> None:
    if current_user.get("role") != "admin":
        return
    if await is_document_in_batch_scope(
        current_user,
        document=section,
        department_field="department_id",
        batch_field="batch_id",
        database=db,
    ):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Section is outside your assigned scope")


async def _sync_section_groups_for_document(section: dict) -> dict[str, int]:
    section_id = str(section.get("_id") or "")
    section_name = str(section.get("name") or "").strip()
    if not section_id or not section_name:
        return {"created": 0, "reactivated": 0, "updated": 0, "skipped": 0}

    summary = {"created": 0, "reactivated": 0, "updated": 0, "skipped": 0}

    for slot in AUTO_SECTION_GROUP_SLOTS:
        group_name, group_code = _build_auto_group_identity(section_name, slot)
        existing_auto_group = await db.groups.find_one(
            {
                "section_id": section_id,
                "auto_generated": True,
                "auto_group_slot": slot,
            }
        )

        if existing_auto_group:
            duplicate = await db.groups.find_one(
                {
                    "section_id": section_id,
                    "code": group_code,
                    "_id": {"$ne": existing_auto_group.get("_id")},
                    "is_active": True,
                }
            )
            if duplicate:
                summary["skipped"] += 1
                continue

            set_fields = {"schema_version": GROUP_SCHEMA_VERSION, "auto_generated": True, "auto_group_slot": slot}
            changed = False
            if existing_auto_group.get("name") != group_name:
                set_fields["name"] = group_name
                changed = True
            if existing_auto_group.get("code") != group_code:
                set_fields["code"] = group_code
                changed = True
            if existing_auto_group.get("is_active") is False:
                set_fields["is_active"] = True
                changed = True

            if changed:
                persist_public_id_update(existing_auto_group, set_fields, kind="group")
                await db.groups.update_one(
                    {"_id": existing_auto_group["_id"]},
                    {
                        "$set": set_fields,
                        "$unset": {"deleted_at": "", "deleted_by": ""},
                    },
                )
                if existing_auto_group.get("is_active") is False:
                    summary["reactivated"] += 1
                else:
                    summary["updated"] += 1
            continue

        duplicate = await db.groups.find_one({"section_id": section_id, "code": group_code, "is_active": True})
        if duplicate:
            summary["skipped"] += 1
            continue

        await db.groups.insert_one(
            persist_public_id(
            {
                "section_id": section_id,
                "name": group_name,
                "code": group_code,
                "description": None,
                "is_active": True,
                "created_at": datetime.now(timezone.utc),
                "schema_version": GROUP_SCHEMA_VERSION,
                "auto_generated": True,
                "auto_group_slot": slot,
            },
            kind="group",
            )
        )
        summary["created"] += 1

    return summary


async def _sync_all_section_groups(
    section_id: str | None = None,
    *,
    current_user: dict[str, Any] | None = None,
) -> dict[str, int]:
    summary = {"section_count": 0, "created": 0, "reactivated": 0, "updated": 0, "skipped": 0}

    if section_id:
        section = await db.classes.find_one({"_id": parse_object_id(section_id), "is_active": True})
        if not section:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Section not found")
        if current_user:
            await _ensure_admin_can_access_section(current_user, section)
        summary["section_count"] = 1
        section_summary = await _sync_section_groups_for_document(section)
        for key in ("created", "reactivated", "updated", "skipped"):
            summary[key] += section_summary[key]
        return summary

    query: dict[str, Any] = {"is_active": True}
    if current_user:
        query = await _apply_admin_scope_to_query(current_user, query)

    async for section in db.classes.find(query):
        summary["section_count"] += 1
        section_summary = await _sync_section_groups_for_document(section)
        for key in ("created", "reactivated", "updated", "skipped"):
            summary[key] += section_summary[key]

    return summary


async def _validate_section_relations(
    *,
    faculty_id: str | None,
    department_id: str | None,
    program_id: str | None,
    specialization_id: str | None,
    batch_id: str | None,
    semester_id: str | None,
) -> None:
    if faculty_id:
        faculty = await db.faculties.find_one({'_id': parse_object_id(faculty_id)})
        if not faculty:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Faculty not found for provided faculty_id')

    if department_id:
        department = await db.departments.find_one({'_id': parse_object_id(department_id)})
        if not department:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Department not found for provided department_id')
        if faculty_id and department.get('faculty_id') != faculty_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='department_id does not belong to provided faculty_id')

    if program_id:
        program = await db.programs.find_one({'_id': parse_object_id(program_id)})
        if not program:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Program not found for provided program_id')
        if department_id and program.get('department_id') != department_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='program_id does not belong to provided department_id')

    if specialization_id:
        specialization = await db.specializations.find_one({'_id': parse_object_id(specialization_id)})
        if not specialization:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Specialization not found for provided specialization_id')
        if program_id and specialization.get('program_id') != program_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='specialization_id does not belong to provided program_id')

    batch = None
    if batch_id:
        batch = await db.batches.find_one({'_id': parse_object_id(batch_id)})
        if not batch:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Batch not found for provided batch_id')
        if program_id and batch.get('program_id') != program_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='batch_id does not belong to provided program_id')
        try:
            validate_batch_specialization_scope(
                batch_specialization_id=batch.get('specialization_id'),
                child_specialization_id=specialization_id,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    if semester_id:
        semester = await db.semesters.find_one({'_id': parse_object_id(semester_id)})
        if not semester:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Semester not found for provided semester_id')
        if batch_id and semester.get('batch_id') != batch_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='semester_id does not belong to provided batch_id')


async def _ensure_section_parent_update_is_safe(*, section_id: str, current: dict[str, Any], update_data: dict[str, Any]) -> None:
    lineage_fields = (
        "faculty_id",
        "department_id",
        "program_id",
        "specialization_id",
        "batch_id",
        "semester_id",
    )
    lineage_changed = any(update_data.get(field, current.get(field)) != current.get(field) for field in lineage_fields if field in update_data)
    if not lineage_changed:
        return

    descendant_checks = (
        ("students", {"class_id": section_id, "is_active": True}, "active students"),
        ("enrollments", {"class_id": section_id}, "enrollments"),
        ("course_offerings", {"section_id": section_id, "is_active": True}, "active course offerings"),
        ("timetables", {"class_id": section_id, "is_active": True}, "active timetables"),
        ("timetable_subject_teacher_maps", {"class_id": section_id}, "subject-teacher timetable maps"),
    )
    for collection_name, query, label in descendant_checks:
        collection = getattr(db, collection_name, None)
        if collection is None:
            continue
        if await collection.find_one(query):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Section parent update would invalidate {label}. "
                    "Move or archive descendant records before changing the section hierarchy."
                ),
            )


async def _ensure_section_delete_is_safe(section_id: str) -> None:
    blocking_checks = (
        ("students", {"class_id": section_id, "is_active": True}, "active students"),
        ("enrollments", {"class_id": section_id}, "enrollments"),
        ("course_offerings", {"section_id": section_id, "is_active": True}, "active course offerings"),
        ("timetables", {"class_id": section_id, "is_active": True}, "active timetables"),
        ("timetable_subject_teacher_maps", {"class_id": section_id}, "subject-teacher timetable maps"),
    )
    for collection_name, query, label in blocking_checks:
        collection = getattr(db, collection_name, None)
        if collection is None:
            continue
        if await collection.find_one(query):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Section cannot be archived while {label} still reference it. "
                    "Archive or move those descendant records first."
                ),
            )


async def _build_section_dashboard_item(section: dict[str, Any]) -> SectionOperationalSummaryOut:
    section_id = str(section.get("_id") or "")
    enrolled_rows = await db.enrollments.find({"class_id": section_id}).to_list(length=5000)
    enrolled_student_ids = {
        str(item.get("student_id"))
        for item in enrolled_rows
        if item.get("student_id")
    }
    student_count = len(enrolled_student_ids)

    legacy_students = await db.students.find({"class_id": section_id, "is_active": True}, {"_id": 1}).to_list(length=5000)
    legacy_profile_only_count = sum(1 for item in legacy_students if str(item.get("_id")) not in enrolled_student_ids)

    active_offering_rows = await db.course_offerings.find({"section_id": section_id, "is_active": True}, {"_id": 1}).to_list(length=5000)
    offering_ids = [str(item["_id"]) for item in active_offering_rows if item.get("_id")]

    slot_ids: list[str] = []
    if offering_ids:
        slot_rows = await db.class_slots.find(
            {"course_offering_id": {"$in": offering_ids}, "is_active": True},
            {"_id": 1},
        ).to_list(length=5000)
        slot_ids = [str(item["_id"]) for item in slot_rows if item.get("_id")]

    pending_evaluation_count = 0
    unreleased_evaluation_count = 0
    if enrolled_student_ids:
        evaluation_rows = await db.evaluations.find(
            {"student_user_id": {"$in": sorted(enrolled_student_ids)}},
            {"is_finalized": 1, "result_status": 1},
        ).to_list(length=10000)
        pending_evaluation_count = sum(1 for item in evaluation_rows if not item.get("is_finalized"))
        unreleased_evaluation_count = sum(1 for item in evaluation_rows if item.get("is_finalized") and item.get("result_status") != "released")

    latest_timetable = await db.timetables.find_one(
        {"class_id": section_id, "status": "published", "is_active": True},
        sort=[("version", -1)],
    )
    latest_timetable_status = None
    latest_timetable_sync_status = None
    latest_timetable_drift_count = 0
    if latest_timetable:
        latest_timetable_status = latest_timetable.get("status")
        sync_snapshot = await _compute_sync_snapshot(latest_timetable)
        latest_timetable_sync_status = sync_snapshot["sync_status"]
        latest_timetable_drift_count = sync_snapshot["drift_count"]

    average_attendance_percent = None
    shortage_risk_count = 0
    if slot_ids:
        attendance_summary = await build_attendance_section_summary(section_id=section_id, database=db)
        average_attendance_percent = attendance_summary.average_attendance_percent
        shortage_risk_count = attendance_summary.shortage_risk_count

    return SectionOperationalSummaryOut(
        section_id=section_id,
        section_name=str(section.get("name") or ""),
        student_count=student_count,
        legacy_profile_only_count=legacy_profile_only_count,
        active_offering_count=len(active_offering_rows),
        pending_evaluation_count=pending_evaluation_count,
        unreleased_evaluation_count=unreleased_evaluation_count,
        latest_timetable_status=latest_timetable_status,
        latest_timetable_sync_status=latest_timetable_sync_status,
        latest_timetable_drift_count=latest_timetable_drift_count,
        average_attendance_percent=average_attendance_percent,
        shortage_risk_count=shortage_risk_count,
    )


@router.get('/', response_model=List[SectionOut])
async def list_sections(
    faculty_id: str | None = Query(default=None),
    department_id: str | None = Query(default=None),
    program_id: str | None = Query(default=None),
    specialization_id: str | None = Query(default=None),
    batch_id: str | None = Query(default=None),
    semester_id: str | None = Query(default=None),
    faculty_name: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[SectionOut]:
    query: dict[str, Any] = {}
    if faculty_id:
        query['faculty_id'] = faculty_id
    if department_id:
        query['department_id'] = department_id
    if program_id:
        query['program_id'] = program_id
    if specialization_id:
        query['specialization_id'] = specialization_id
    if batch_id:
        query['batch_id'] = batch_id
    if semester_id:
        query['semester_id'] = semester_id
    if faculty_name:
        query['faculty_name'] = faculty_name
    if q:
        query['name'] = {'$regex': q, '$options': 'i'}
    apply_is_active_filter(query, is_active)
    if current_user.get('role') == 'teacher':
        if "class_coordinator" not in set(current_user.get("extended_roles") or []):
            return []
        query['class_coordinator_user_id'] = str(current_user.get('_id'))
        scoped_class_id = coordinator_scope_class_id(current_user)
        if scoped_class_id:
            query['_id'] = parse_object_id(scoped_class_id)
        query.setdefault('is_active', True)
    else:
        query = await _apply_admin_scope_to_query(current_user, query)

    cursor = db.classes.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    items = await hydrate_sections_from_read_models(source_sections=items, database=db)
    return [SectionOut(**section_public(item)) for item in items]


@router.get('/dashboard', response_model=SectionDashboardResponse)
async def section_dashboard(
    faculty_id: str | None = Query(default=None),
    department_id: str | None = Query(default=None),
    program_id: str | None = Query(default=None),
    specialization_id: str | None = Query(default=None),
    batch_id: str | None = Query(default=None),
    semester_id: str | None = Query(default=None),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> SectionDashboardResponse:
    query: dict[str, Any] = {"is_active": True}
    if faculty_id:
        query['faculty_id'] = faculty_id
    if department_id:
        query['department_id'] = department_id
    if program_id:
        query['program_id'] = program_id
    if specialization_id:
        query['specialization_id'] = specialization_id
    if batch_id:
        query['batch_id'] = batch_id
    if semester_id:
        query['semester_id'] = semester_id

    if current_user.get("role") == "teacher":
        coordinator_section_id = coordinator_scope_class_id(current_user)
        if coordinator_section_id:
            query["_id"] = parse_object_id(coordinator_section_id)
        else:
            query["class_coordinator_user_id"] = str(current_user.get("_id"))
    else:
        query = await _apply_admin_scope_to_query(current_user, query)

    sections = await db.classes.find(query).to_list(length=500)
    items: list[SectionOperationalSummaryOut] = []
    for section in sections:
        items.append(await _build_section_dashboard_item(section))

    global_unmapped_query: dict[str, Any] = {"is_active": True}
    if batch_id:
        global_unmapped_query["batch_id"] = batch_id
    if semester_id:
        global_unmapped_query["semester_id"] = semester_id
    global_unmapped_students = await db.students.count_documents(
        {
            "is_active": True,
            "$or": [{"class_id": None}, {"class_id": ""}, {"class_id": {"$exists": False}}],
        }
    )

    return SectionDashboardResponse(
        total_sections=len(items),
        total_students=sum(item.student_count for item in items),
        total_active_offerings=sum(item.active_offering_count for item in items),
        total_pending_evaluations=sum(item.pending_evaluation_count for item in items),
        total_unreleased_evaluations=sum(item.unreleased_evaluation_count for item in items),
        sections_with_drift=sum(1 for item in items if item.latest_timetable_drift_count > 0),
        sections_with_attendance_risk=sum(1 for item in items if item.shortage_risk_count > 0),
        global_unmapped_students=global_unmapped_students,
        sections=items,
    )


@router.post('/sync-groups')
async def sync_section_groups(
    section_id: str | None = Query(default=None),
    current_user=Depends(require_permission("sections.manage")),
) -> dict[str, int]:
    return await _sync_all_section_groups(section_id, current_user=current_user)


@router.post('/{section_id}/lock', response_model=SectionOut)
async def lock_section_mapping(
    section_id: str,
    payload: SectionLockRequest,
    request: Request,
    current_user=Depends(require_permission("sections.lock_mapping")),
) -> SectionOut:
    section = await get_section_or_404(section_id)
    await _ensure_admin_can_access_section(current_user, section)
    if not can_lock_or_unlock_section(current_user, section):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to lock this section")

    now = datetime.now(timezone.utc)
    update_fields = {
        "mapping_locked": True,
        "mapping_locked_by_user_id": str(current_user.get("_id")),
        "mapping_locked_by_name": current_user.get("full_name"),
        "mapping_locked_by_email": current_user.get("email"),
        "mapping_locked_at": now,
        "mapping_lock_reason": payload.reason.strip() if payload.reason else None,
        "schema_version": CLASS_SCHEMA_VERSION,
    }
    await db.classes.update_one({"_id": section["_id"]}, {"$set": update_fields})
    updated = await db.classes.find_one({"_id": section["_id"]})
    await log_audit_event(
        actor_user_id=str(current_user.get("_id") or ""),
        action="sections.mapping_lock",
        entity_type="section",
        entity_id=section_id,
        detail=f"Section mapping locked for {updated.get('name')}",
        new_value=section_mapping_lock_state(updated),
        ip_address=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        severity="medium",
    )
    return SectionOut(**section_public(updated))


@router.post('/{section_id}/unlock', response_model=SectionOut)
async def unlock_section_mapping(
    section_id: str,
    payload: SectionLockRequest,
    request: Request,
    current_user=Depends(require_permission("sections.lock_mapping")),
) -> SectionOut:
    section = await get_section_or_404(section_id)
    await _ensure_admin_can_access_section(current_user, section)
    if not can_lock_or_unlock_section(current_user, section):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed to unlock this section")

    current_user_id = str(current_user.get("_id") or "")
    locked_by_user_id = str(section.get("mapping_locked_by_user_id") or "")
    if current_user.get("role") != "admin" and locked_by_user_id and locked_by_user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only the locking coordinator or admin can unlock this section")

    await db.classes.update_one(
        {"_id": section["_id"]},
        {
            "$set": {"mapping_locked": False, "schema_version": CLASS_SCHEMA_VERSION},
            "$unset": {
                "mapping_locked_by_user_id": "",
                "mapping_locked_by_name": "",
                "mapping_locked_by_email": "",
                "mapping_locked_at": "",
                "mapping_lock_reason": "",
            },
        },
    )
    updated = await db.classes.find_one({"_id": section["_id"]})
    await log_audit_event(
        actor_user_id=str(current_user.get("_id") or ""),
        action="sections.mapping_unlock",
        entity_type="section",
        entity_id=section_id,
        detail=f"Section mapping unlocked for {updated.get('name')}",
        old_value=section_mapping_lock_state(section),
        new_value=section_mapping_lock_state(updated),
        ip_address=request.headers.get("x-forwarded-for") or (request.client.host if request.client else None),
        user_agent=request.headers.get("user-agent"),
        severity="medium",
    )
    return SectionOut(**section_public(updated))


@router.get('/{section_id}', response_model=SectionOut)
async def get_section(
    section_id: str,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> SectionOut:
    item = await db.classes.find_one({'_id': parse_object_id(section_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')
    if current_user.get('role') == 'teacher':
        if not is_section_coordinator(current_user, item):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to view this class')
    else:
        await _ensure_admin_can_access_section(current_user, item)
    item = await get_section_read_model(section_id=section_id, database=db)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')
    return SectionOut(**section_public(item))


@router.post('/', response_model=SectionOut, status_code=status.HTTP_201_CREATED)
async def create_section(
    payload: SectionCreate,
    current_user=Depends(require_permission("sections.manage")),
) -> SectionOut:
    await _validate_section_relations(
        faculty_id=payload.faculty_id,
        department_id=payload.department_id,
        program_id=payload.program_id,
        specialization_id=payload.specialization_id,
        batch_id=payload.batch_id,
        semester_id=payload.semester_id,
    )
    await _ensure_admin_can_access_section(
        current_user,
        {"department_id": payload.department_id, "batch_id": payload.batch_id},
    )
    await validate_section_coordinator_user(payload.class_coordinator_user_id)

    document = {
        'faculty_id': payload.faculty_id,
        'department_id': payload.department_id,
        'program_id': payload.program_id,
        'specialization_id': payload.specialization_id,
        'batch_id': payload.batch_id,
        'semester_id': payload.semester_id,
        'name': payload.name.strip(),
        'faculty_name': payload.faculty_name.strip() if payload.faculty_name else None,
        'class_coordinator_user_id': payload.class_coordinator_user_id,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'schema_version': CLASS_SCHEMA_VERSION,
    }
    persist_public_id(document, kind='section')
    result = await db.classes.insert_one(document)
    created = await db.classes.find_one({'_id': result.inserted_id})
    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Section creation failed')
    if payload.class_coordinator_user_id is not None:
        created, _ = await sync_section_coordinator_assignment(
            section_id=str(created["_id"]),
            coordinator_user_id=payload.class_coordinator_user_id,
        )
    await _sync_section_groups_for_document(created)
    created = await sync_section_read_model(section=created, database=db)
    return SectionOut(**section_public(created))


@router.put('/{section_id}', response_model=SectionOut)
async def update_section(
    section_id: str,
    payload: SectionUpdate,
    current_user=Depends(require_permission("sections.manage")),
) -> SectionOut:
    class_obj_id = parse_object_id(section_id)
    current = await db.classes.find_one({'_id': class_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')
    await _ensure_admin_can_access_section(current_user, current)

    update_data = payload.model_dump(exclude_unset=True)
    if 'name' in update_data and update_data['name']:
        update_data['name'] = update_data['name'].strip()
    if 'faculty_name' in update_data and update_data['faculty_name']:
        update_data['faculty_name'] = update_data['faculty_name'].strip()

    target_faculty_id = update_data.get('faculty_id', current.get('faculty_id'))
    target_department_id = update_data.get('department_id', current.get('department_id'))
    target_program_id = update_data.get('program_id', current.get('program_id'))
    target_specialization_id = update_data.get('specialization_id', current.get('specialization_id'))
    target_batch_id = update_data.get('batch_id', current.get('batch_id'))
    target_semester_id = update_data.get('semester_id', current.get('semester_id'))
    await _validate_section_relations(
        faculty_id=target_faculty_id,
        department_id=target_department_id,
        program_id=target_program_id,
        specialization_id=target_specialization_id,
        batch_id=target_batch_id,
        semester_id=target_semester_id,
    )
    await _ensure_admin_can_access_section(
        current_user,
        {"department_id": target_department_id, "batch_id": target_batch_id},
    )
    if 'class_coordinator_user_id' in update_data:
        await validate_section_coordinator_user(update_data.get('class_coordinator_user_id'))

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')
    await _ensure_section_parent_update_is_safe(section_id=section_id, current=current, update_data=update_data)
    persist_public_id_update(current, update_data, kind='section')
    update_data['schema_version'] = CLASS_SCHEMA_VERSION

    result = await db.classes.update_one({'_id': class_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')
    updated = await db.classes.find_one({'_id': class_obj_id})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')
    if 'class_coordinator_user_id' in update_data:
        updated, _ = await sync_section_coordinator_assignment(
            section_id=section_id,
            coordinator_user_id=update_data.get('class_coordinator_user_id'),
            previous_coordinator_user_id=current.get('class_coordinator_user_id'),
        )
    await _sync_section_groups_for_document(updated)
    updated = await sync_section_read_model(section=updated, database=db)
    return SectionOut(**section_public(updated))


@router.delete('/{section_id}')
async def delete_section(
    section_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("sections.manage")),
) -> dict:
    section = await db.classes.find_one({'_id': parse_object_id(section_id)})
    if not section:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')
    await _ensure_admin_can_access_section(current_user, section)
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="sections.delete",
        entity_type="section",
        entity_id=section_id,
        stage="requested",
        detail="Section delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="sections.delete",
        entity_type="section",
        entity_id=section_id,
    ))
    await _ensure_section_delete_is_safe(section_id)
    result = await db.classes.update_one(
        {'_id': parse_object_id(section_id), 'is_active': True},
        build_soft_delete_update(
            deleted_by=str(current_user.get('_id')),
            extra_fields={'schema_version': CLASS_SCHEMA_VERSION},
        ),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Section not found')
    archived = await db.classes.find_one({'_id': parse_object_id(section_id)})
    if archived:
        await sync_section_read_model(section=archived, database=db)
    await db.groups.update_many(
        {"section_id": section_id, "is_active": True},
        build_soft_delete_update(
            deleted_by=str(current_user.get('_id')),
            extra_fields={'schema_version': GROUP_SCHEMA_VERSION},
        ),
    )
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="sections.delete",
        entity_type="section",
        entity_id=section_id,
        stage="completed",
        detail="Section archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {'message': 'Section archived'}


# Compatibility aliases are retained while tests and older internal imports
# still reference class-named endpoint symbols.
list_classes = list_sections
get_class = get_section
create_class = create_section
update_class = update_section
delete_class = delete_section
