from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.departments import department_public
from app.schemas.department import DepartmentCreate, DepartmentOut, DepartmentUpdate

router = APIRouter()


@router.get('/', response_model=List[DepartmentOut])
async def list_departments(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[DepartmentOut]:
    query = {}
    if q:
        query['$or'] = [
            {'name': {'$regex': q, '$options': 'i'}},
            {'code': {'$regex': q, '$options': 'i'}},
        ]
    if is_active is not None:
        query['is_active'] = is_active

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
    _current_user=Depends(require_roles(['admin'])),
) -> DepartmentOut:
    normalized_code = payload.code.strip().upper()
    existing = await db.departments.find_one({'code': normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Department code already exists')

    document = {
        'name': payload.name.strip(),
        'code': normalized_code,
        'university_name': payload.university_name.strip() if payload.university_name else None,
        'university_code': payload.university_code.strip().upper() if payload.university_code else None,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
    }
    result = await db.departments.insert_one(document)
    created = await db.departments.find_one({'_id': result.inserted_id})
    return DepartmentOut(**department_public(created))


@router.put('/{department_id}', response_model=DepartmentOut)
async def update_department(
    department_id: str,
    payload: DepartmentUpdate,
    _current_user=Depends(require_roles(['admin'])),
) -> DepartmentOut:
    department_obj_id = parse_object_id(department_id)
    current = await db.departments.find_one({'_id': department_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    update_data = payload.model_dump(exclude_none=True)
    if 'name' in update_data and update_data['name']:
        update_data['name'] = update_data['name'].strip()
    if 'code' in update_data and update_data['code']:
        update_data['code'] = update_data['code'].strip().upper()
        duplicate = await db.departments.find_one({'code': update_data['code']})
        if duplicate and duplicate.get('_id') != department_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Department code already exists')
    if 'university_name' in update_data and update_data['university_name']:
        update_data['university_name'] = update_data['university_name'].strip()
    if 'university_code' in update_data and update_data['university_code']:
        update_data['university_code'] = update_data['university_code'].strip().upper()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    result = await db.departments.update_one({'_id': department_obj_id}, {'$set': update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    updated = await db.departments.find_one({'_id': department_obj_id})
    if updated:
        branch_set = {'department_name': updated['name']}
        if updated.get('code') != current.get('code'):
            branch_set['department_code'] = updated['code']
        await db.branches.update_many(
            {'department_code': current.get('code')},
            {'$set': branch_set},
        )
    return DepartmentOut(**department_public(updated))


@router.delete('/{department_id}')
async def delete_department(
    department_id: str,
    current_user=Depends(require_roles(['admin'])),
) -> dict:
    department_obj_id = parse_object_id(department_id)
    department = await db.departments.find_one({'_id': department_obj_id})
    if not department:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')

    await db.branches.update_many(
        {'department_code': department.get('code')},
        {'$set': {'is_active': False}},
    )
    result = await db.departments.update_one(
        {'_id': department_obj_id, 'is_active': True},
        {'$set': {'is_active': False, 'is_deleted': True, 'deleted_at': datetime.now(timezone.utc), 'deleted_by': str(current_user.get('_id'))}},
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Department not found')
    return {'message': 'Department archived'}
