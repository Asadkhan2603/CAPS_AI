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
    faculty_name: str | None = Query(default=None),
    branch_name: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[ClassOut]:
    query = {}
    if course_id:
        query['course_id'] = course_id
    if year_id:
        query['year_id'] = year_id
    if faculty_name:
        query['faculty_name'] = faculty_name
    if branch_name:
        query['branch_name'] = branch_name
    if q:
        query['name'] = {'$regex': q, '$options': 'i'}
    if is_active is not None:
        query['is_active'] = is_active
    if current_user.get('role') == 'teacher':
        query['class_coordinator_user_id'] = str(current_user.get('_id'))
        query.setdefault('is_active', True)

    cursor = db.classes.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [ClassOut(**class_public(item)) for item in items]


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
    return ClassOut(**class_public(item))


@router.post('/', response_model=ClassOut, status_code=status.HTTP_201_CREATED)
async def create_class(
    payload: ClassCreate,
    _current_user=Depends(require_roles(['admin'])),
) -> ClassOut:
    course = await db.courses.find_one({'_id': parse_object_id(payload.course_id)})
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Course not found for provided course_id')

    year = await db.years.find_one({'_id': parse_object_id(payload.year_id)})
    if not year:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Year not found for provided year_id')

    if year.get('course_id') != payload.course_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='year_id does not belong to provided course_id',
        )

    document = {
        'course_id': payload.course_id,
        'year_id': payload.year_id,
        'name': payload.name.strip(),
        'faculty_name': payload.faculty_name.strip() if payload.faculty_name else None,
        'branch_name': payload.branch_name.strip() if payload.branch_name else None,
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
    class_obj_id = parse_object_id(class_id)
    current = await db.classes.find_one({'_id': class_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')

    update_data = payload.model_dump(exclude_none=True)
    if 'name' in update_data and update_data['name']:
        update_data['name'] = update_data['name'].strip()
    if 'faculty_name' in update_data and update_data['faculty_name']:
        update_data['faculty_name'] = update_data['faculty_name'].strip()
    if 'branch_name' in update_data and update_data['branch_name']:
        update_data['branch_name'] = update_data['branch_name'].strip()

    target_course_id = update_data.get('course_id', current.get('course_id'))
    target_year_id = update_data.get('year_id', current.get('year_id'))
    if target_course_id and target_year_id:
        course = await db.courses.find_one({'_id': parse_object_id(target_course_id)})
        if not course:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Course not found for provided course_id',
            )
        year = await db.years.find_one({'_id': parse_object_id(target_year_id)})
        if not year:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Year not found for provided year_id',
            )
        if year.get('course_id') != target_course_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='year_id does not belong to provided course_id',
            )

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    result = await db.classes.update_one({'_id': class_obj_id}, {'$set': update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Class not found')
    updated = await db.classes.find_one({'_id': class_obj_id})
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
