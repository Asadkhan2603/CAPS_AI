from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.models.clubs import club_public
from app.schemas.club import ClubCreate, ClubOut
from app.services.audit import log_audit_event

router = APIRouter()


@router.get('/', response_model=List[ClubOut])
async def list_clubs(
    is_active: bool | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[ClubOut]:
    query = {}
    if is_active is not None:
        query['is_active'] = is_active
    items = await db.clubs.find(query).skip(skip).limit(limit).to_list(length=limit)
    return [ClubOut(**club_public(item)) for item in items]


@router.post('/', response_model=ClubOut, status_code=status.HTTP_201_CREATED)
async def create_club(
    payload: ClubCreate,
    current_user=Depends(require_roles(['admin'])),
) -> ClubOut:
    if payload.coordinator_user_id:
        teacher = await db.users.find_one({'_id': parse_object_id(payload.coordinator_user_id)})
        if not teacher:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Coordinator not found')
        if teacher.get('role') != 'teacher':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Coordinator must be a teacher')

    document = {
        'name': payload.name.strip(),
        'description': payload.description,
        'coordinator_user_id': payload.coordinator_user_id,
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
    }
    result = await db.clubs.insert_one(document)
    created = await db.clubs.find_one({'_id': result.inserted_id})

    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='create',
        entity_type='club',
        entity_id=str(result.inserted_id),
        detail='Created club',
    )
    return ClubOut(**club_public(created))
