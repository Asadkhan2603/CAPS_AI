from datetime import datetime, timezone
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission, require_roles
from app.core.soft_delete import apply_is_active_filter, build_soft_delete_update, build_state_update
from app.models.years import year_public
from app.schemas.year import YearCreate, YearOut, YearUpdate
from app.services.audit import log_destructive_action_event
from app.services.governance import enforce_review_approval

router = APIRouter()


@router.get('/', response_model=List[YearOut])
async def list_years(
    course_id: str | None = Query(default=None),
    year_number: int | None = Query(default=None, ge=1, le=10),
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[YearOut]:
    query: dict[str, Any] = {}
    if course_id:
        query['course_id'] = course_id
    if year_number is not None:
        query['year_number'] = year_number
    if q:
        query['label'] = {'$regex': q, '$options': 'i'}
    apply_is_active_filter(query, is_active)

    cursor = db.years.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [YearOut(**year_public(item)) for item in items]


@router.get('/{year_id}', response_model=YearOut)
async def get_year(
    year_id: str,
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> YearOut:
    item = await db.years.find_one({'_id': parse_object_id(year_id)})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Year not found')
    return YearOut(**year_public(item))


@router.post('/', response_model=YearOut, status_code=status.HTTP_201_CREATED)
async def create_year(
    payload: YearCreate,
    _current_user=Depends(require_permission("years.manage")),
) -> YearOut:
    course = await db.courses.find_one({'_id': parse_object_id(payload.course_id)})
    if not course:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Course not found for provided course_id')

    existing = await db.years.find_one({'course_id': payload.course_id, 'year_number': payload.year_number})
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Year already exists for this course and year number',
        )

    document = {
        'course_id': payload.course_id,
        'year_number': payload.year_number,
        'label': payload.label.strip(),
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
    }
    result = await db.years.insert_one(document)
    created = await db.years.find_one({'_id': result.inserted_id})
    if not created:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Year creation failed')
    return YearOut(**year_public(created))


@router.put('/{year_id}', response_model=YearOut)
async def update_year(
    year_id: str,
    payload: YearUpdate,
    _current_user=Depends(require_permission("years.manage")),
) -> YearOut:
    year_obj_id = parse_object_id(year_id)
    current = await db.years.find_one({'_id': year_obj_id})
    if not current:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Year not found')

    update_data = payload.model_dump(exclude_none=True)
    if 'label' in update_data and update_data['label']:
        update_data['label'] = update_data['label'].strip()
    if 'year_number' in update_data:
        duplicate = await db.years.find_one(
            {
                'course_id': current['course_id'],
                'year_number': update_data['year_number'],
            }
        )
        if duplicate and duplicate.get('_id') != year_obj_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Year already exists for this course and year number',
            )
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No fields to update')

    result = await db.years.update_one({'_id': year_obj_id}, build_state_update(update_data))
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Year not found')
    updated = await db.years.find_one({'_id': year_obj_id})
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Year not found')
    return YearOut(**year_public(updated))


@router.delete('/{year_id}')
async def delete_year(
    year_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("years.manage")),
) -> dict:
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="years.delete",
        entity_type="year",
        entity_id=year_id,
        stage="requested",
        detail="Year delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="years.delete",
        entity_type="year",
        entity_id=year_id,
    ))
    result = await db.years.update_one(
        {'_id': parse_object_id(year_id), 'is_active': True},
        build_soft_delete_update(deleted_by=str(current_user.get('_id'))),
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Year not found')
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="years.delete",
        entity_type="year",
        entity_id=year_id,
        stage="completed",
        detail="Year archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return {'message': 'Year archived'}
