from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.database import db
from app.core.observability import build_operational_alerts, observability_state
from app.core.security import require_permission
from app.services.ai_jobs import sample_ai_queue_metrics
from app.services.operational_alert_routing import route_operational_alert_notifications
from app.services.scheduler import app_scheduler
from app.services.system_health_snapshots import (
    get_system_health_snapshot_history,
    get_system_health_snapshot_store_status,
    persist_system_health_snapshot,
)

router = APIRouter()
_APP_BOOT_TIME = datetime.now(timezone.utc)


def _as_utc_datetime(value):
    if value is None:
        return None
    if isinstance(value, str):
        candidate = value.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1] + "+00:00"
        try:
            value = datetime.fromisoformat(candidate)
        except ValueError:
            return None
    if not isinstance(value, datetime):
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


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
        expires_at = _as_utc_datetime(scheduler_lock_doc.get('expires_at'))
        heartbeat_at = _as_utc_datetime(scheduler_lock_doc.get('heartbeat_at'))
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
    await sample_ai_queue_metrics(database=db)
    observability = observability_state.snapshot()
    alerts = build_operational_alerts(
        db_status=db_status,
        scheduler_status=scheduler_status,
        scheduler_lock=scheduler_lock_doc,
        snapshot=observability,
    )

    payload = {
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
    await persist_system_health_snapshot(payload=payload, database=db)
    payload['snapshot_history'] = await get_system_health_snapshot_history(database=db)
    payload['snapshot_store'] = await get_system_health_snapshot_store_status(database=db)
    if not payload['snapshot_store']['is_within_retention_bound']:
        payload['alerts'].append(
            {
                'level': 'medium',
                'code': 'system_health_snapshots.retention_drift',
                'message': (
                    'Persisted system health snapshots exceed the configured retention bound: '
                    f"{payload['snapshot_store']['retained_rows']} rows stored with a configured cap of "
                    f"{payload['snapshot_store']['max_retained_rows']}."
                ),
            }
        )
        payload['alert_count'] = len(payload['alerts'])
    payload['alert_routing'] = await route_operational_alert_notifications(
        alerts=payload["alerts"],
        database=db,
        now=now,
    )
    return payload
