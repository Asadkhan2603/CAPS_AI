from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.courses import course_public
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate

router = APIRouter()


@router.get('/', response_model=List[CourseOut])
async def list_courses(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[CourseOut]:
    query = {}
    if q:
        query['$or'] = [
            {'name': {'$regex': q, '$options': 'i'}},
            {'code': {'$regex': q, '$options': 'i'}},
        ]
    if is_active is not None:
        query['is_active'] = is_active

    cursor = db.courses.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [CourseOut(**course_public(item)) for item in items]


@router.get('/{course_id}', response_model=CourseOut)
async def get_course(
    course_id: str,
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> CourseOut:
    item = await db.courses.find_one({'_id': parse_object_id(course_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Course not found')
    return CourseOut(**course_public(item))


@router.post('/', response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    _current_user=Depends(require_roles(['admin'])),
) -> CourseOut:
    normalized_code = payload.code.strip().upper()
    existing = await db.courses.find_one({'code': normalized_code})
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Course code already exists')

    document = {
        'name': payload.name.strip(),
        'code': normalized_code,
        'description': payload.description,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
    }
    result = await db.courses.insert_one(document)
    created = await db.courses.find_one({'_id': result.inserted_id})
    return CourseOut(**course_public(created))


@router.put('/{course_id}', response_model=CourseOut)
async def update_course(
    course_id: str,
    payload: CourseUpdate,
    _current_user=Depends(require_roles(['admin'])),
) -> CourseOut:
    course_obj_id = parse_object_id(course_id)
    update_data = payload.model_dump(exclude_none=True)
    if 'name' in update_data and update_data['name']:
        update_data['name'] = update_data['name'].strip()
    if 'code' in update_data and update_data['code']:
        update_data['code'] = update_data['code'].strip().upper()
        duplicate = await db.courses.find_one({'code': update_data['code']})
        if duplicate and duplicate.get('_id') != course_obj_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Course code already exists')
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    result = await db.courses.update_one({'_id': course_obj_id}, {'$set': update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Course not found')
    updated = await db.courses.find_one({'_id': course_obj_id})
    return CourseOut(**course_public(updated))


@router.delete('/{course_id}')
async def delete_course(
    course_id: str,
    _current_user=Depends(require_roles(['admin'])),
) -> dict:
    result = await db.courses.delete_one({'_id': parse_object_id(course_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Course not found')
    return {'message': 'Course deleted'}
