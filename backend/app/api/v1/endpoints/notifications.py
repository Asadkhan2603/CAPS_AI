from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_roles
from app.core.schema_versions import NOTIFICATION_SCHEMA_VERSION
from app.models.notifications import notification_public
from app.schemas.notification import NotificationCreate, NotificationOut
from app.services.communication_deliveries import (
    default_delivery_summary,
    get_delivery_read_map,
    get_delivery_summaries,
    mark_delivery_read,
)
from app.services.communication_preferences import resolve_notification_delivery_preferences
from app.services.audit import log_audit_event
from app.services.notifications import create_notification

router = APIRouter()


async def _hydrate_notifications(items: list[dict], *, current_user_id: str) -> list[dict]:
    notification_ids = [str(item.get("_id")) for item in items if item.get("_id")]
    summaries = await get_delivery_summaries(source_kind="notification", source_ids=notification_ids)
    read_map = await get_delivery_read_map(
        source_kind="notification",
        source_ids=notification_ids,
        target_user_id=current_user_id,
    )
    hydrated = []
    for item in items:
        source_id = str(item.get("_id") or "")
        payload = dict(item)
        payload["delivery_summary"] = summaries.get(source_id, default_delivery_summary())
        payload["current_user_delivery_read"] = read_map.get(source_id, bool(item.get("is_read", False)))
        hydrated.append(payload)
    return hydrated


async def get_unread_notification_count_payload(
    current_user,
) -> dict:
    current_user_id = str(current_user["_id"])
    items = await db.notifications.find(
        {"$or": [{"target_user_id": None}, {"target_user_id": current_user_id}]}
    ).to_list(length=5000)
    items = [item for item in items if resolve_notification_delivery_preferences(current_user, scope=item.get("scope")).get("in_app", True)]
    hydrated = await _hydrate_notifications(items, current_user_id=current_user_id)
    count = sum(1 for item in hydrated if not item.get("current_user_delivery_read"))
    return {"count": count}


@router.get('/', response_model=List[NotificationOut])
async def list_notifications(
    is_read: bool | None = Query(default=None),
    scope: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[NotificationOut]:
    query = {'$or': [{'target_user_id': None}, {'target_user_id': str(current_user['_id'])}]}
    if scope:
        query['scope'] = scope

    items = await db.notifications.find(query).sort('created_at', -1).to_list(length=max(skip + limit + 200, 200))
    items = [item for item in items if resolve_notification_delivery_preferences(current_user, scope=item.get("scope")).get("in_app", True)]
    hydrated = await _hydrate_notifications(items, current_user_id=str(current_user['_id']))
    if is_read is not None:
        hydrated = [item for item in hydrated if bool(item.get("current_user_delivery_read")) is is_read]
    page = hydrated[skip: skip + limit]
    return [NotificationOut(**notification_public(item)) for item in page]


@router.get('/unread-count')
async def get_unread_notification_count(
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> dict:
    return await get_unread_notification_count_payload(current_user)


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

    read_target_user_id = str(current_user['_id'])
    if target_user_id and current_user.get('role') == 'admin' and target_user_id != read_target_user_id:
        read_target_user_id = target_user_id

    await db.notifications.update_one(
        {'_id': notification_obj_id},
        {'$set': {'is_read': True, 'schema_version': NOTIFICATION_SCHEMA_VERSION}},
    )
    await mark_delivery_read(
        source_kind='notification',
        source_id=str(notification_obj_id),
        target_user_id=read_target_user_id,
    )
    updated = await db.notifications.find_one({'_id': notification_obj_id})
    hydrated = await _hydrate_notifications([updated], current_user_id=str(current_user['_id']))
    return NotificationOut(**notification_public(hydrated[0]))
