from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.database import db
from app.core.security import require_permission
from app.services.analytics_snapshot import compute_platform_snapshot, get_daily_snapshot, get_snapshot_history

router = APIRouter()


async def _overview_payload() -> dict:
    now = datetime.now(timezone.utc)
    day_ago = now.replace(microsecond=0) - timedelta(hours=24)
    week_ahead = now + timedelta(days=7)
    return {
        'total_users': await db.users.count_documents({}),
        'active_students': await db.students.count_documents({'is_active': True}),
        'active_clubs': await db.clubs.count_documents({'status': {'$in': ['active', 'registration_closed']}}),
        'pending_review_tickets': await db.review_tickets.count_documents({'status': {'$in': ['pending', 'open']}}),
        'assignments_total': await db.assignments.count_documents({}),
        'submissions_total': await db.submissions.count_documents({}),
        'events_this_week': await db.club_events.count_documents({'event_date': {'$gte': now, '$lte': week_ahead}}),
        'system_errors_24h': await db.audit_logs.count_documents(
            {
                'created_at': {'$gte': day_ago},
                '$or': [
                    {'action': {'$in': ['error', 'exception']}},
                    {'severity': 'high'},
                ],
            }
        ),
    }


@router.get('/overview')
async def admin_analytics_overview(
    _current_user=Depends(require_permission('analytics.read')),
) -> dict:
    return {
        'timestamp': datetime.now(timezone.utc),
        'overview': await _overview_payload(),
    }


@router.get('/platform')
async def admin_analytics_platform(
    _current_user=Depends(require_permission('analytics.read')),
) -> dict:
    snapshot = await get_daily_snapshot()
    if not snapshot:
        snapshot = await compute_platform_snapshot()
    return {
        'timestamp': datetime.now(timezone.utc),
        'metrics': snapshot,
    }


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
