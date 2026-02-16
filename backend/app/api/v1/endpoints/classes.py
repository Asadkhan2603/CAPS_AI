from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.classes import class_public
from app.schemas.class_item import ClassCreate, ClassOut, ClassUpdate

router = APIRouter()


@router.get('/', response_model=List[ClassOut])
async def list_classes(
    course_id: str | None = Query(default=None),
    year_id: str | None = Query(default=None),
    section: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[ClassOut]:
    query = {}
    if course_id:
        query['course_id'] = course_id
    if year_id:
        query['year_id'] = year_id
    if section:
        query['section'] = section
    if q:
        query['name'] = {'$regex': q, '$options': 'i'}
    if is_active is not None:
        query['is_active'] = is_active

    cursor = db.classes.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [ClassOut(**class_public(item)) for item in items]


@router.get('/{class_id}', response_model=ClassOut)
async def get_class(
    class_id: str,
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> ClassOut:
    item = await db.classes.find_one({'_id': parse_object_id(class_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    return ClassOut(**class_public(item))


@router.post('/', response_model=ClassOut, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate,
    _current_user=Depends(require_roles(['admin'])),
) -> ClassOut:
    document = {
        'course_id': payload.course_id,
        'year_id': payload.year_id,
        'name': payload.name.strip(),
        'section': payload.section,
        'class_coordinator_user_id': payload.class_coordinator_user_id,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
    }
    result = await db.classes.insert_one(document)
    created = await db.classes.find_one({'_id': result.inserted_id})
    return ClassOut(**class_public(created))


@router.put('/{class_id}', response_model=ClassOut)
async def update_class(
    class_id: str,
    payload: ClassUpdate,
    _current_user=Depends(require_roles(['admin'])),
) -> ClassOut:
    update_data = payload.model_dump(exclude_none=True)
    if 'name' in update_data and update_data['name']:
        update_data['name'] = update_data['name'].strip()
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    result = await db.classes.update_one({'_id': parse_object_id(class_id)}, {'$set': update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    updated = await db.classes.find_one({'_id': parse_object_id(class_id)})
    return ClassOut(**class_public(updated))


@router.delete('/{class_id}')
async def delete_class(
    class_id: str,
    _current_user=Depends(require_roles(['admin'])),
) -> dict:
    result = await db.classes.delete_one({'_id': parse_object_id(class_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    return {'message': 'Class deleted'}
