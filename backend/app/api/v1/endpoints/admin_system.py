from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.database import db
from app.core.observability import build_operational_alerts, observability_state
from app.core.security import require_permission
from app.services.scheduler import app_scheduler

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

    scheduler_status = app_scheduler.status()
    scheduler_lock_doc = None
    scheduler_lock = {
        'owner_id': None,
        'expires_at': None,
        'heartbeat_at': None,
        'is_stale': None,
    }
    try:
        scheduler_lock_doc = await db.scheduler_locks.find_one({'_id': scheduler_status['lock_id']})
    except Exception:
        scheduler_lock_doc = None
    if scheduler_lock_doc:
        expires_at = scheduler_lock_doc.get('expires_at')
        heartbeat_at = scheduler_lock_doc.get('heartbeat_at')
        scheduler_lock = {
            'owner_id': scheduler_lock_doc.get('owner_id'),
            'expires_at': expires_at,
            'heartbeat_at': heartbeat_at,
            'is_stale': bool(expires_at and expires_at <= now),
        }

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
    observability = observability_state.snapshot()
    alerts = build_operational_alerts(
        db_status=db_status,
        scheduler_status=scheduler_status,
        scheduler_lock=scheduler_lock_doc,
        snapshot=observability,
    )

    return {
        'timestamp': now,
        'db_status': db_status,
        'scheduler': scheduler_status,
        'scheduler_lock': scheduler_lock,
        'observability': observability,
        'alerts': alerts,
        'alert_count': len(alerts),
        'uptime_seconds': int((now - _APP_BOOT_TIME).total_seconds()),
        'error_count_24h': error_count_24h,
        'active_sessions_24h': len(active_sessions_24h),
        'slow_query_count_24h': slow_query_count_24h,
        'slow_query_logs': slow_query_logs,
        'collection_counts': collection_counts,
    }
