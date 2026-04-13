from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLASS_SCHEMA_VERSION
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.classes import class_public
from app.schemas.class_item import ClassCreate, ClassOut, ClassUpdate
from app.schemas.section import SectionDashboardResponse, SectionOperationalSummaryOut
from app.services.academic_hierarchy import validate_batch_specialization_scope
from app.services.audit import log_destructive_action_event
from app.services.attendance_summary import build_attendance_section_summary
from app.services.class_slot_read_models import sync_class_slot_read_models_for_offering_query
from app.services.course_offering_read_models import sync_course_offering_read_models_for_query
from app.services.governance import enforce_review_approval
from app.services.public_ids import persist_public_id, persist_public_id_update
from app.services.rbac import build_batch_scope_filter, merge_query_with_scope_filter
from app.services.section_read_models import (
    get_section_read_model,
    hydrate_sections_from_read_models,
    sync_section_read_model,
)
from app.services.section_mapping import coordinator_scope_class_id
from app.api.v1.endpoints.timetables import _compute_sync_snapshot

router = APIRouter()


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


async def _build_section_dashboard_item(section: dict[str, Any]) -> SectionOperationalSummaryOut:
    section_id = str(section.get("_id") or "")
    enrolled_rows = await db.enrollments.find({"class_id": section_id}).to_list(length=5000)
    enrolled_student_doc_ids = {
        str(item.get("student_id"))
        for item in enrolled_rows
        if item.get("student_id")
    }
    student_count = len(enrolled_student_doc_ids)

    legacy_students = await db.students.find({"class_id": section_id, "is_active": True}, {"_id": 1}).to_list(length=5000)
    legacy_profile_only_count = sum(1 for item in legacy_students if str(item.get("_id")) not in enrolled_student_doc_ids)

    enrolled_student_user_ids: set[str] = set()
    if enrolled_student_doc_ids:
        enrolled_student_rows = await db.students.find(
            {"_id": {"$in": [parse_object_id(student_id) for student_id in sorted(enrolled_student_doc_ids)]}},
            {"user_id": 1},
        ).to_list(length=5000)
        enrolled_student_user_ids = {
            str(item.get("user_id"))
            for item in enrolled_student_rows
            if item.get("user_id")
        }

    active_offering_rows = await db.course_offerings.find({"section_id": section_id, "is_active": True}, {"_id": 1}).to_list(length=5000)
    offering_ids = [str(item["_id"]) for item in active_offering_rows if item.get("_id")]

    pending_evaluation_count = 0
    unreleased_evaluation_count = 0
    if enrolled_student_user_ids:
        evaluation_rows = await db.evaluations.find(
            {"student_user_id": {"$in": sorted(enrolled_student_user_ids)}},
            {"is_finalized": 1, "result_status": 1},
        ).to_list(length=10000)
        pending_evaluation_count = sum(1 for item in evaluation_rows if not item.get("is_finalized"))
        unreleased_evaluation_count = sum(
            1 for item in evaluation_rows if item.get("is_finalized") and item.get("result_status") != "released"
        )

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
    if active_offering_rows and getattr(db, "attendance_records", None) is not None:
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


@router.get('/', response_model=List[ClassOut])
async def list_classes(
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
) -> List[ClassOut]:
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
        query['class_coordinator_user_id'] = str(current_user.get('_id'))
        query.setdefault('is_active', True)
    else:
        query = await _apply_admin_scope_to_query(current_user, query)

    cursor = db.classes.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    items = await hydrate_sections_from_read_models(source_sections=items, database=db)
    return [ClassOut(**class_public(item)) for item in items]


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
        query["faculty_id"] = faculty_id
    if department_id:
        query["department_id"] = department_id
    if program_id:
        query["program_id"] = program_id
    if specialization_id:
        query["specialization_id"] = specialization_id
    if batch_id:
        query["batch_id"] = batch_id
    if semester_id:
        query["semester_id"] = semester_id

    if current_user.get("role") == "teacher":
        scoped_class_id = coordinator_scope_class_id(current_user)
        if scoped_class_id:
            query["_id"] = parse_object_id(scoped_class_id)
        else:
            query["class_coordinator_user_id"] = str(current_user.get("_id"))
    else:
        query = await _apply_admin_scope_to_query(current_user, query)

    sections = await db.classes.find(query).to_list(length=500)
    items = [await _build_section_dashboard_item(section) for section in sections]

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


@router.get('/{class_id}', response_model=ClassOut)
async def get_class(
    class_id: str,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> ClassOut:
    item = await db.classes.find_one({'_id': parse_object_id(class_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    if current_user.get('role') == 'teacher':
        if item.get('class_coordinator_user_id') != str(current_user.get('_id')):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to view this class')
    item = await get_section_read_model(section_id=class_id, database=db)
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    return ClassOut(**class_public(item))


@router.post('/', response_model=ClassOut, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate,
    _current_user=Depends(require_permission("sections.manage")),
) -> ClassOut:
    await _validate_section_relations(
        faculty_id=payload.faculty_id,
        department_id=payload.department_id,
        program_id=payload.program_id,
        specialization_id=payload.specialization_id,
        batch_id=payload.batch_id,
        semester_id=payload.semester_id,
    )

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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Class creation failed')
    created = await sync_section_read_model(section=created, database=db)
    return ClassOut(**class_public(created))


@router.put('/{class_id}', response_model=ClassOut)
async def update_class(
    class_id: str,
    payload: ClassUpdate,
    _current_user=Depends(require_permission("sections.manage")),
) -> ClassOut:
    class_obj_id = parse_object_id(class_id)
    current = await db.classes.find_one({'_id': class_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')

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

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')
    persist_public_id_update(current, update_data, kind='section')
    update_data['schema_version'] = CLASS_SCHEMA_VERSION

    result = await db.classes.update_one({'_id': class_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    updated = await db.classes.find_one({'_id': class_obj_id})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    updated = await sync_section_read_model(section=updated, database=db)
    await sync_course_offering_read_models_for_query(query={"section_id": class_id}, database=db)
    await sync_class_slot_read_models_for_offering_query(offering_query={"section_id": class_id}, database=db)
    return ClassOut(**class_public(updated))


@router.delete('/{class_id}')
async def delete_class(
    class_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("sections.manage")),
) -> dict:
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="classes.delete",
        entity_type="class",
        entity_id=class_id,
        stage="requested",
        detail="Class delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="classes.delete",
        entity_type="class",
        entity_id=class_id,
    ))
    result = await db.classes.update_one(
        {'_id': parse_object_id(class_id), 'is_active': True},
        build_soft_delete_update(
            deleted_by=str(current_user.get('_id')),
            extra_fields={'schema_version': CLASS_SCHEMA_VERSION},
        ),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    archived = await db.classes.find_one({'_id': parse_object_id(class_id)})
    if archived:
        await sync_section_read_model(section=archived, database=db)
    await sync_course_offering_read_models_for_query(query={"section_id": class_id}, database=db)
    await sync_class_slot_read_models_for_offering_query(offering_query={"section_id": class_id}, database=db)
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="classes.delete",
        entity_type="class",
        entity_id=class_id,
        stage="completed",
        detail="Class archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {'message': 'Class archived'}
