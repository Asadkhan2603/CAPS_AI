from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.branches import branch_public
from app.schemas.branch import BranchCreate, BranchOut, BranchUpdate

router = APIRouter()


@router.get('/', response_model=List[BranchOut])
async def list_branches(
    department_code: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=200),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[BranchOut]:
    query = {}
    if department_code:
        query['department_code'] = department_code.strip().upper()
    if q:
        query['$or'] = [
            {'name': {'$regex': q, '$options': 'i'}},
            {'code': {'$regex': q, '$options': 'i'}},
            {'department_name': {'$regex': q, '$options': 'i'}},
        ]
    if is_active is not None:
        query['is_active'] = is_active

    cursor = db.branches.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [BranchOut(**branch_public(item)) for item in items]


@router.get('/{branch_id}', response_model=BranchOut)
async def get_branch(
    branch_id: str,
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> BranchOut:
    item = await db.branches.find_one({'_id': parse_object_id(branch_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Branch not found')
    return BranchOut(**branch_public(item))


@router.post('/', response_model=BranchOut, status_code=status.HTTP_201_CREATED)
async def create_branch(
    payload: BranchCreate,
    _current_user=Depends(require_roles(['admin'])),
) -> BranchOut:
    normalized_code = payload.code.strip().upper()
    normalized_department_code = payload.department_code.strip().upper()

    existing = await db.branches.find_one({'code': normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Branch code already exists')

    department = await db.departments.find_one({'code': normalized_department_code})
    if not department:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Department not found for provided department_code')

    document = {
        'name': payload.name.strip(),
        'code': normalized_code,
        'department_name': department.get('name'),
        'department_code': normalized_department_code,
        'university_name': payload.university_name.strip() if payload.university_name else department.get('university_name'),
        'university_code': payload.university_code.strip().upper() if payload.university_code else department.get('university_code'),
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
    }
    result = await db.branches.insert_one(document)
    created = await db.branches.find_one({'_id': result.inserted_id})
    return BranchOut(**branch_public(created))


@router.put('/{branch_id}', response_model=BranchOut)
async def update_branch(
    branch_id: str,
    payload: BranchUpdate,
    _current_user=Depends(require_roles(['admin'])),
) -> BranchOut:
    branch_obj_id = parse_object_id(branch_id)
    update_data = payload.model_dump(exclude_none=True)
    if 'name' in update_data and update_data['name']:
        update_data['name'] = update_data['name'].strip()
    if 'code' in update_data and update_data['code']:
        update_data['code'] = update_data['code'].strip().upper()
        duplicate = await db.branches.find_one({'code': update_data['code']})
        if duplicate and duplicate.get('_id') != branch_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Branch code already exists')
    if 'department_code' in update_data and update_data['department_code']:
        update_data['department_code'] = update_data['department_code'].strip().upper()
        department = await db.departments.find_one({'code': update_data['department_code']})
        if not department:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Department not found for provided department_code')
        update_data['department_name'] = department.get('name')
    if 'university_name' in update_data and update_data['university_name']:
        update_data['university_name'] = update_data['university_name'].strip()
    if 'university_code' in update_data and update_data['university_code']:
        update_data['university_code'] = update_data['university_code'].strip().upper()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    result = await db.branches.update_one({'_id': branch_obj_id}, {'$set': update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Branch not found')
    updated = await db.branches.find_one({'_id': branch_obj_id})
    return BranchOut(**branch_public(updated))


@router.delete('/{branch_id}')
async def delete_branch(
    branch_id: str,
    _current_user=Depends(require_roles(['admin'])),
) -> dict:
    result = await db.branches.delete_one({'_id': parse_object_id(branch_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Branch not found')
    return {'message': 'Branch deleted'}
