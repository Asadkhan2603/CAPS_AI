from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission
from app.core.soft_delete import build_restore_update, build_soft_deleted_query
from app.services.audit import log_audit_event
from app.services.public_ids import build_user_label

router = APIRouter()

LEGACY_RECOVERY_COLLECTIONS = {
    'branches',
    'courses',
    'years',
}

ACTIVE_RECOVERY_COLLECTIONS = {
    'departments',
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

RECOVERY_COLLECTIONS = ACTIVE_RECOVERY_COLLECTIONS | LEGACY_RECOVERY_COLLECTIONS

RECOVERY_COLLECTION_META = {
    'departments': {'label': 'Departments', 'group': 'Academic structure', 'legacy': False},
    'classes': {'label': 'Classes', 'group': 'Academic structure', 'legacy': False},
    'notices': {'label': 'Notices', 'group': 'Communication', 'legacy': False},
    'notifications': {'label': 'Notifications', 'group': 'Communication', 'legacy': False},
    'assignments': {'label': 'Assignments', 'group': 'Student work', 'legacy': False},
    'submissions': {'label': 'Submissions', 'group': 'Student work', 'legacy': False},
    'evaluations': {'label': 'Evaluations', 'group': 'Student work', 'legacy': False},
    'review_tickets': {'label': 'Review Tickets', 'group': 'Student work', 'legacy': False},
    'clubs': {'label': 'Clubs', 'group': 'Clubs', 'legacy': False},
    'club_events': {'label': 'Club Events', 'group': 'Clubs', 'legacy': False},
    'branches': {'label': 'Branches', 'group': 'Legacy', 'legacy': True},
    'courses': {'label': 'Courses', 'group': 'Legacy', 'legacy': True},
    'years': {'label': 'Years', 'group': 'Legacy', 'legacy': True},
}
RECOVERY_COLLECTION_ORDER = [
    'departments',
    'classes',
    'notices',
    'notifications',
    'assignments',
    'submissions',
    'evaluations',
    'review_tickets',
    'clubs',
    'club_events',
    'branches',
    'courses',
    'years',
]


@router.get('/')
async def list_recovery_items(
    collection: str | None = Query(default=None),
    include_legacy: bool = Query(
        default=False,
        description='Include retired legacy compatibility collections such as courses, years, and branches.',
    ),
    limit: int = Query(default=100, ge=1, le=500),
    _current_user=Depends(require_permission('system.read')),
) -> dict:
    available_collections = [
        target for target in RECOVERY_COLLECTION_ORDER
        if target in (RECOVERY_COLLECTIONS if include_legacy else ACTIVE_RECOVERY_COLLECTIONS)
    ]
    targets = [collection] if collection else available_collections
    for target in targets:
        if target not in RECOVERY_COLLECTIONS:
            raise HTTPException(status_code=400, detail=f'Unsupported recovery collection: {target}')

    deleted_by_lookup = await _load_deleted_by_lookup(targets)
    data = {}
    for target in targets:
        rows = await db[target].find(
            build_soft_deleted_query(include_legacy_marker=True)
        ).limit(limit).to_list(length=limit)

        data[target] = [
            _serialize_recovery_item(target, item, deleted_by_lookup)
            for item in rows
        ]

    summary = {
        target: len(data.get(target, []))
        for target in targets
    }

    return {
        'timestamp': datetime.now(timezone.utc),
        'catalog': [
            {
                'key': key,
                'label': RECOVERY_COLLECTION_META[key]['label'],
                'legacy': RECOVERY_COLLECTION_META[key]['legacy'],
                'group': RECOVERY_COLLECTION_META[key]['group'],
            }
            for key in available_collections
        ],
        'items': data,
        'summary': summary,
        'legacy_collections_included': include_legacy,
    }


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
        build_restore_update(restored_by=str(current_user.get('_id'))),
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
    recovery_logs = getattr(db, "recovery_logs", None)
    if recovery_logs is not None:
        await recovery_logs.insert_one(
            {
                "collection": collection,
                "entity_id": item_id,
                "action": "restore",
                "performed_by": str(current_user.get("_id")),
                "created_at": datetime.now(timezone.utc),
            }
        )

    return {'success': True, 'collection': collection, 'id': item_id, 'message': 'Item restored'}


async def _load_deleted_by_lookup(targets: list[str]) -> dict[str, str]:
    deleted_by_values = set()
    for target in targets:
        rows = await db[target].find(
            build_soft_deleted_query(include_legacy_marker=True)
        ).limit(500).to_list(length=500)
        for item in rows:
            deleted_by = item.get('deleted_by')
            if deleted_by:
                deleted_by_values.add(str(deleted_by))

    users_collection = getattr(db, 'users', None)
    if users_collection is None or not deleted_by_values:
        return {}

    object_ids = [parse_object_id(value) for value in deleted_by_values if _is_object_id(value)]
    if not object_ids:
        return {}

    users = await users_collection.find({'_id': {'$in': object_ids}}, {'full_name': 1, 'email': 1}).to_list(length=len(object_ids))
    return {
        str(user.get('_id')): build_user_label(
            user.get('_id'),
            full_name=user.get('full_name'),
            email=user.get('email'),
        ) or str(user.get('_id'))
        for user in users
    }


def _serialize_recovery_item(collection: str, item: dict, deleted_by_lookup: dict[str, str]) -> dict:
    deleted_by = item.get('deleted_by')
    deleted_by_value = str(deleted_by) if deleted_by is not None else None
    public_id = item.get('public_id')
    return {
        'id': str(item.get('_id')),
        'name': item.get('name') or item.get('title') or item.get('full_name') or '-',
        'display_name': _build_display_name(item),
        'subtitle': _build_subtitle(item),
        'status_label': _build_status_label(item),
        'is_deleted': item.get('deleted_at') is not None,
        'is_active': item.get('is_active'),
        'deleted_at': item.get('deleted_at'),
        'deleted_by': deleted_by,
        'deleted_by_label': deleted_by_lookup.get(deleted_by_value) or deleted_by_value,
        'audit_resource_type': collection,
        'public_id': public_id,
    }


def _build_display_name(item: dict) -> str:
    for field_name in ('name', 'title', 'full_name', 'subject_name', 'reason', 'original_filename', 'public_id', 'code'):
        value = str(item.get(field_name) or '').strip()
        if value:
            return value
    item_id = str(item.get('_id') or '').strip()
    return item_id or '-'


def _build_subtitle(item: dict) -> str:
    for field_name in ('code', 'email', 'public_id', 'roll_number', 'status'):
        value = str(item.get(field_name) or '').strip()
        if value:
            if field_name == 'status':
                return f'Status: {value.replace("_", " ").title()}'
            return value
    return 'N/A'


def _build_status_label(item: dict) -> str:
    status = str(item.get('status') or '').strip()
    if status:
        return status.replace('_', ' ').title()
    is_active = item.get('is_active')
    if is_active is True:
        return 'Active'
    if is_active is False:
        return 'Inactive'
    return 'Unknown'


def _is_object_id(value: str) -> bool:
    try:
        parse_object_id(str(value))
    except HTTPException:
        return False
    return True
