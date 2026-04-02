from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query

from app.core.config import settings
from app.core.security import require_permission
from app.services.analytics_snapshot import (
    build_admin_analytics_overview,
    compute_platform_snapshot,
    get_latest_snapshot,
    get_snapshot_history,
)

router = APIRouter()


async def _analytics_bootstrap_payload(*, refresh: bool = False) -> dict:
    snapshot = None
    snapshot_age_hours = None
    if not refresh:
        snapshot, snapshot_age_hours = await get_latest_snapshot(
            max_age_hours=max(1, int(settings.analytics_snapshot_freshness_hours))
        )
    if not snapshot:
        snapshot = await compute_platform_snapshot()
        snapshot_age_hours = 0
        snapshot_served_from = "live"
    else:
        snapshot_served_from = "snapshot"

    return {
        'timestamp': datetime.now(timezone.utc),
        'overview': build_admin_analytics_overview(snapshot),
        'metrics': snapshot,
        'snapshot_served_from': snapshot_served_from,
        'snapshot_age_hours': snapshot_age_hours,
    }


@router.get('/overview')
async def admin_analytics_overview(
    refresh: bool = Query(False),
    _current_user=Depends(require_permission('analytics.read')),
) -> dict:
    payload = await _analytics_bootstrap_payload(refresh=refresh)
    return {
        'timestamp': payload['timestamp'],
        'overview': payload['overview'],
        'snapshot_served_from': payload['snapshot_served_from'],
        'snapshot_age_hours': payload['snapshot_age_hours'],
    }


@router.get('/platform')
async def admin_analytics_platform(
    refresh: bool = Query(False),
    _current_user=Depends(require_permission('analytics.read')),
) -> dict:
    payload = await _analytics_bootstrap_payload(refresh=refresh)
    return {
        'timestamp': payload['timestamp'],
        'metrics': payload['metrics'],
        'snapshot_served_from': payload['snapshot_served_from'],
        'snapshot_age_hours': payload['snapshot_age_hours'],
    }


@router.get('/bootstrap')
async def admin_analytics_bootstrap(
    refresh: bool = Query(False),
    _current_user=Depends(require_permission('analytics.read')),
) -> dict:
    return await _analytics_bootstrap_payload(refresh=refresh)


@router.post('/snapshots/run-daily')
async def run_daily_snapshot(
    _current_user=Depends(require_permission('analytics.read')),
) -> dict:
    snapshot = await compute_platform_snapshot()
    return {'timestamp': datetime.now(timezone.utc), 'snapshot': snapshot}


@router.get('/snapshots/history')
async def snapshots_history(
    limit: int = 30,
    _current_user=Depends(require_permission('analytics.read')),
) -> dict:
    rows = await get_snapshot_history(limit=max(1, min(120, int(limit))))
    return {'timestamp': datetime.now(timezone.utc), 'items': rows}


@router.get('/audit-summary')
async def admin_audit_summary(
    _current_user=Depends(require_permission('audit.read')),
) -> dict:
    now = datetime.now(timezone.utc)
    day_ago = now - timedelta(hours=24)

    low = await db.audit_logs.count_documents({'created_at': {'$gte': day_ago}, 'severity': 'low'})
    medium = await db.audit_logs.count_documents({'created_at': {'$gte': day_ago}, 'severity': 'medium'})
    high = await db.audit_logs.count_documents({'created_at': {'$gte': day_ago}, 'severity': 'high'})
    total = low + medium + high

    top_actions = await db.audit_logs.aggregate(
        [
            {'$match': {'created_at': {'$gte': day_ago}}},
            {'$group': {'_id': '$action_type', 'count': {'$sum': 1}}},
            {'$sort': {'count': -1}},
            {'$limit': 5},
        ]
    ).to_list(length=5)

    return {
        'timestamp': now,
        'window_hours': 24,
        'severity': {
            'low': low,
            'medium': medium,
            'high': high,
            'total': total,
        },
        'top_actions': [{'action_type': item.get('_id') or 'unknown', 'count': item.get('count', 0)} for item in top_actions],
    }
