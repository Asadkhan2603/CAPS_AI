from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission
from app.services.audit import log_audit_event

router = APIRouter()

RECOVERY_COLLECTIONS = {
    'courses',
    'departments',
    'branches',
    'years',
    'classes',
    'notices',
    'notifications',
    'clubs',
    'club_events',
    'assignments',
    'submissions',
    'evaluations',
    'review_tickets',
}


@router.get('/')
async def list_recovery_items(
    collection: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    _current_user=Depends(require_permission('system.read')),
) -> dict:
    targets = [collection] if collection else sorted(RECOVERY_COLLECTIONS)
    for target in targets:
        if target not in RECOVERY_COLLECTIONS:
            raise HTTPException(status_code=400, detail=f'Unsupported recovery collection: {target}')

    data = {}
    for target in targets:
        rows = await db[target].find(
            {
                '$or': [
                    {'is_deleted': True},
                    {'$and': [{'is_active': False}, {'deleted_at': {'$ne': None}}]},
                ]
            }
        ).limit(limit).to_list(length=limit)

        data[target] = [
            {
                'id': str(item.get('_id')),
                'name': item.get('name') or item.get('title') or item.get('full_name') or '-',
                'is_deleted': bool(item.get('is_deleted', False)),
                'is_active': item.get('is_active'),
                'deleted_at': item.get('deleted_at'),
                'deleted_by': item.get('deleted_by'),
            }
            for item in rows
        ]

    summary = {
        target: len(data.get(target, []))
        for target in targets
    }

    return {'timestamp': datetime.now(timezone.utc), 'items': data, 'summary': summary}


@router.patch('/{collection}/{item_id}/restore')
async def restore_item(
    collection: str,
    item_id: str,
    current_user=Depends(require_permission('system.read')),
) -> dict:
    if collection not in RECOVERY_COLLECTIONS:
        raise HTTPException(status_code=400, detail='Unsupported recovery collection')

    obj_id = parse_object_id(item_id)
    current = await db[collection].find_one({'_id': obj_id})
    if not current:
        raise HTTPException(status_code=404, detail='Item not found')

    await db[collection].update_one(
        {'_id': obj_id},
        {
            '$set': {
                'is_deleted': False,
                'is_active': True,
                'restored_at': datetime.now(timezone.utc),
                'restored_by': str(current_user.get('_id')),
            },
            '$unset': {'deleted_at': '', 'deleted_by': ''},
        },
    )

    await log_audit_event(
        actor_user_id=str(current_user.get('_id')),
        action='restore',
        action_type='restore',
        entity_type=collection,
        resource_type=collection,
        entity_id=item_id,
        detail=f"Restored soft-deleted {collection} item",
        severity='medium',
    )

    return {'success': True, 'collection': collection, 'id': item_id, 'message': 'Item restored'}
