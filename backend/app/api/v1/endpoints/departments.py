from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import BRANCH_SCHEMA_VERSION, DEPARTMENT_SCHEMA_VERSION
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.departments import department_public
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate
from app.services.master_hierarchy import (
    build_department_business_id,
    coalesce_code,
    coalesce_text,
    ensure_master_hierarchy_change_is_safe,
    normalize_code,
)
from app.services.public_ids import persist_public_id, persist_public_id_update
from app.services.audit import log_destructive_action_event
from app.services.governance import enforce_review_approval
from app.services.section_read_models import sync_section_read_models_for_query

router = APIRouter()


def _materialize_department_fields(payload: DepartmentCreate | DepartmentUpdate) -> tuple[str | None, str | None, str | None]:
    department_name = coalesce_text(getattr(payload, "department_name", None), getattr(payload, "name", None))
    department_code = coalesce_code(getattr(payload, "department_code", None), getattr(payload, "code", None))
    department_id = normalize_code(getattr(payload, "department_id", None))
    return department_name, department_code, department_id


async def _resolve_department_lineage(
    *,
    faculty_id: str | None,
    faculty_master_id: str | None,
) -> dict[str, Any] | None:
    faculty = None
    if faculty_id:
        faculty = await db.faculties.find_one({"_id": parse_object_id(faculty_id)})
        if not faculty:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty not found for provided faculty_id")
    elif faculty_master_id:
        faculty = await db.faculties.find_one({"faculty_id": normalize_code(faculty_master_id)})
        if not faculty:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Faculty not found for provided faculty_master_id")
    return faculty


@router.get('/', response_model=List[DepartmentOut])
async def list_departments(
    faculty_id: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[DepartmentOut]:
    query: dict[str, Any] = {}
    if faculty_id:
        query['faculty_id'] = faculty_id
    if q:
        query['$or'] = [
            {'department_name': {'$regex': q, '$options': 'i'}},
            {'name': {'$regex': q, '$options': 'i'}},
            {'department_code': {'$regex': q, '$options': 'i'}},
            {'code': {'$regex': q, '$options': 'i'}},
            {'department_id': {'$regex': q, '$options': 'i'}},
        ]
    apply_is_active_filter(query, is_active)

    cursor = db.departments.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [DepartmentOut(**department_public(item)) for item in items]


@router.get('/{department_id}', response_model=DepartmentOut)
async def get_department(
    department_id: str,
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> DepartmentOut:
    item = await db.departments.find_one({'_id': parse_object_id(department_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')
    return DepartmentOut(**department_public(item))


@router.post('/', response_model=DepartmentOut, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    _current_user=Depends(require_permission("departments.manage")),
) -> DepartmentOut:
    faculty = await _resolve_department_lineage(
        faculty_id=payload.faculty_id,
        faculty_master_id=payload.faculty_master_id,
    )
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Department must be linked to an existing faculty',
        )
    department_name, department_code, department_id = _materialize_department_fields(payload)
    if not department_name or not department_code:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Department name and code are required')
    if faculty and not department_id:
        try:
            department_id = build_department_business_id(
                faculty_code=str(faculty.get('faculty_code') or faculty.get('code') or ''),
                department_code=department_code,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not department_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='department_id could not be generated from faculty and department code')
    existing = await db.departments.find_one(
        {
            '$or': [
                {'department_id': department_id},
                {'faculty_id': str(faculty['_id']) if faculty else None, 'department_code': department_code},
                {'faculty_id': str(faculty['_id']) if faculty else None, 'code': department_code},
            ]
        }
    )
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Department ID or code already exists')

    document = {
        'department_id': department_id,
        'department_code': department_code,
        'department_name': department_name,
        'name': department_name,
        'code': department_code,
        'faculty_id': str(faculty['_id']) if faculty else None,
        'faculty_master_id': str(faculty.get('faculty_id') or payload.faculty_master_id or '') or None,
        'faculty_code': str(faculty.get('faculty_code') or faculty.get('code') or payload.faculty_code or '').strip().upper() or None,
        'faculty_name': str(faculty.get('faculty_name') or faculty.get('name') or payload.faculty_name or '').strip() or None,
        'university_master_id': str(
            faculty.get('university_master_id') or payload.university_master_id or payload.university_code or ''
        ).strip().upper()
        or None,
        'university_name': str(faculty.get('university_name') or payload.university_name or '').strip() or None,
        'university_code': str(
            faculty.get('university_code') or faculty.get('university_master_id') or payload.university_code or ''
        ).strip().upper()
        or None,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
        'schema_version': DEPARTMENT_SCHEMA_VERSION,
    }
    persist_public_id(document, kind='department')
    result = await db.departments.insert_one(document)
    created = await db.departments.find_one({'_id': result.inserted_id})
    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Department creation failed')
    return DepartmentOut(**department_public(created))


@router.put('/{department_id}', response_model=DepartmentOut)
async def update_department(
    department_id: str,
    payload: DepartmentUpdate,
    _current_user=Depends(require_permission("departments.manage")),
) -> DepartmentOut:
    department_obj_id = parse_object_id(department_id)
    current = await db.departments.find_one({'_id': department_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    update_data = payload.model_dump(exclude_none=True)
    if any(key in update_data for key in ('faculty_name', 'faculty_code', 'university_master_id', 'university_name', 'university_code')) and not any(
        key in update_data for key in ('faculty_id', 'faculty_master_id')
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Department lineage fields are derived from the selected faculty and cannot be edited independently',
        )
    faculty = None
    if 'faculty_id' in update_data or 'faculty_master_id' in update_data:
        faculty = await _resolve_department_lineage(
            faculty_id=update_data.get('faculty_id', current.get('faculty_id')),
            faculty_master_id=update_data.get('faculty_master_id', current.get('faculty_master_id')),
        )
        if not faculty:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Department must remain linked to an existing faculty',
            )
        if str(faculty['_id']) != current.get('faculty_id'):
            try:
                await ensure_master_hierarchy_change_is_safe(
                    db,
                    entity_kind='department',
                    entity_doc_id=department_id,
                    operation='move to another faculty',
                )
            except ValueError as exc:
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    department_name, department_code, department_id = _materialize_department_fields(payload)
    if any(key in update_data for key in ('department_name', 'name')):
        update_data['department_name'] = department_name
        update_data['name'] = department_name
    if any(key in update_data for key in ('department_code', 'code')):
        update_data['department_code'] = department_code
        update_data['code'] = department_code
    effective_department_code = update_data.get('department_code', current.get('department_code') or current.get('code'))
    effective_department_id = update_data.get('department_id', current.get('department_id'))
    if faculty and any(key in update_data for key in ('department_id', 'department_code', 'code', 'faculty_id', 'faculty_master_id')) and not update_data.get('department_id'):
        try:
            effective_department_id = build_department_business_id(
                faculty_code=str(faculty.get('faculty_code') or faculty.get('code') or ''),
                department_code=effective_department_code,
            )
            update_data['department_id'] = effective_department_id
        except ValueError:
            effective_department_id = current.get('department_id')
    if faculty:
        update_data['faculty_id'] = str(faculty['_id'])
        update_data['faculty_master_id'] = str(faculty.get('faculty_id') or '')
        update_data['faculty_code'] = str(faculty.get('faculty_code') or faculty.get('code') or '')
        update_data['faculty_name'] = str(faculty.get('faculty_name') or faculty.get('name') or '')
        update_data['university_master_id'] = str(faculty.get('university_master_id') or faculty.get('university_code') or '')
        update_data['university_name'] = str(faculty.get('university_name') or '')
        update_data['university_code'] = str(faculty.get('university_code') or faculty.get('university_master_id') or '')
    if effective_department_code or effective_department_id:
        duplicate = await db.departments.find_one(
            {
                '_id': {'$ne': department_obj_id},
                '$or': [
                    {'department_id': effective_department_id},
                    {'faculty_id': update_data.get('faculty_id', current.get('faculty_id')), 'department_code': effective_department_code},
                    {'faculty_id': update_data.get('faculty_id', current.get('faculty_id')), 'code': effective_department_code},
                ],
            }
        )
        if duplicate:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Department ID or code already exists')
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')
    persist_public_id_update(current, update_data, kind='department')
    update_data['schema_version'] = DEPARTMENT_SCHEMA_VERSION

    result = await db.departments.update_one({'_id': department_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    updated = await db.departments.find_one({'_id': department_obj_id})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')
    if updated:
        branch_set = {'department_name': updated.get('department_name') or updated['name']}
        if (updated.get('department_code') or updated.get('code')) != (current.get('department_code') or current.get('code')):
            branch_set['department_code'] = updated.get('department_code') or updated.get('code')
        branch_set['schema_version'] = BRANCH_SCHEMA_VERSION
        await db.branches.update_many(
            {'department_code': current.get('department_code') or current.get('code')},
            {'$set': branch_set},
        )
    await sync_section_read_models_for_query(query={"department_id": department_id}, database=db)
    return DepartmentOut(**department_public(updated))


@router.delete('/{department_id}')
async def delete_department(
    department_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("departments.manage")),
) -> dict:
    try:
        await ensure_master_hierarchy_change_is_safe(
            db,
            entity_kind='department',
            entity_doc_id=department_id,
            operation='archive',
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="departments.delete",
        entity_type="department",
        entity_id=department_id,
        stage="requested",
        detail="Department delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="departments.delete",
        entity_type="department",
        entity_id=department_id,
    ))
    department_obj_id = parse_object_id(department_id)
    department = await db.departments.find_one({'_id': department_obj_id})
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    await db.branches.update_many(
        {'department_code': department.get('department_code') or department.get('code')},
        build_soft_delete_update(
            deleted_by=str(current_user.get('_id')),
            extra_fields={"schema_version": BRANCH_SCHEMA_VERSION},
        ),
    )
    result = await db.departments.update_one(
        {'_id': department_obj_id, 'is_active': True},
        build_soft_delete_update(
            deleted_by=str(current_user.get('_id')),
            extra_fields={"schema_version": DEPARTMENT_SCHEMA_VERSION},
        ),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')
    await sync_section_read_models_for_query(query={"department_id": department_id}, database=db)
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="departments.delete",
        entity_type="department",
        entity_id=department_id,
        stage="completed",
        detail="Department archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {'message': 'Department archived'}
