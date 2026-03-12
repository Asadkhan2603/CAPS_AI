from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.core.schema_versions import NOTIFICATION_SCHEMA_VERSION
from app.models.notifications import notification_public
from app.schemas.notification import NotificationCreate, NotificationOut
from app.services.audit import log_audit_event
from app.services.notifications import create_notification

router = APIRouter()


@router.get('/', response_model=List[NotificationOut])
async def list_notifications(
    is_read: bool | None = Query(default=None),
    scope: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[NotificationOut]:
    query = {'$or': [{'target_user_id': None}, {'target_user_id': str(current_user['_id'])}]}
    if is_read is not None:
        query['is_read'] = is_read
    if scope:
        query['scope'] = scope

    cursor = db.notifications.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [NotificationOut(**notification_public(item)) for item in items]


@router.post('/', response_model=NotificationOut, status_code=status.HTTP_201_CREATED)
async def create_notification_item(
    payload: NotificationCreate,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> NotificationOut:
    created = await create_notification(
        title=payload.title,
        message=payload.message,
        priority=payload.priority,
        scope=payload.scope,
        target_user_id=payload.target_user_id,
        created_by=str(current_user['_id']),
    )

    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='create',
        entity_type='notification',
        entity_id=str(created.get('_id')) if created.get('_id') else None,
        detail=f"Notification '{payload.title}' created",
    )

    return NotificationOut(**notification_public(created))


@router.patch('/{notification_id}/read', response_model=NotificationOut)
async def mark_notification_read(
    notification_id: str,
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> NotificationOut:
    notification_obj_id = parse_object_id(notification_id)
    item = await db.notifications.find_one({'_id': notification_obj_id})
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Notification not found')

    target_user_id = item.get('target_user_id')
    if target_user_id and target_user_id != str(current_user['_id']) and current_user.get('role') != 'admin':
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to mark this notification')

    await db.notifications.update_one(
        {'_id': notification_obj_id},
        {'$set': {'is_read': True, 'schema_version': NOTIFICATION_SCHEMA_VERSION}},
    )
    updated = await db.notifications.find_one({'_id': notification_obj_id})
    return NotificationOut(**notification_public(updated))
