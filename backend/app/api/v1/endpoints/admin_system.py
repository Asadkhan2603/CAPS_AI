from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.database import db
from app.core.security import require_permission

router = APIRouter()
_APP_BOOT_TIME = datetime.now(timezone.utc)


@router.get('/health')
async def admin_system_health(
    _current_user=Depends(require_permission('system.read')),
) -> dict:
    now = datetime.now(timezone.utc)
    db_status = 'ok'
    try:
        await db.command('ping')
    except Exception:
        db_status = 'error'

    collection_counts = {}
    for name in ['users', 'students', 'assignments', 'submissions', 'evaluations', 'clubs', 'club_events', 'audit_logs']:
        try:
            collection_counts[name] = await db[name].count_documents({})
        except Exception:
            collection_counts[name] = -1

    day_ago = now - timedelta(hours=24)
    active_sessions_24h = await db.audit_logs.distinct(
        'actor_user_id',
        {
            'action_type': 'login',
            'created_at': {'$gte': day_ago},
            'actor_user_id': {'$ne': None},
        },
    )
    error_count_24h = await db.audit_logs.count_documents(
        {
            'created_at': {'$gte': day_ago},
            '$or': [
                {'action': {'$in': ['error', 'exception']}},
                {'severity': 'high'},
            ],
        }
    )
    slow_query_count_24h = await db.audit_logs.count_documents(
        {
            'created_at': {'$gte': day_ago},
            'action_type': 'slow_query',
        }
    )
    slow_query_rows = await db.audit_logs.find(
        {
            'created_at': {'$gte': day_ago},
            'action_type': 'slow_query',
        },
        {'entity_type': 1, 'detail': 1, 'created_at': 1},
    ).sort('created_at', -1).limit(10).to_list(length=10)
    slow_query_logs = [
        {
            'resource': row.get('entity_type'),
            'detail': row.get('detail'),
            'created_at': row.get('created_at'),
        }
        for row in slow_query_rows
    ]

    return {
        'timestamp': now,
        'db_status': db_status,
        'uptime_seconds': int((now - _APP_BOOT_TIME).total_seconds()),
        'error_count_24h': error_count_24h,
        'active_sessions_24h': len(active_sessions_24h),
        'slow_query_count_24h': slow_query_count_24h,
        'slow_query_logs': slow_query_logs,
        'collection_counts': collection_counts,
    }
