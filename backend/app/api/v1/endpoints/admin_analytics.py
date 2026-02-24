from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from app.core.database import db
from app.core.security import require_permission

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
    now = datetime.now(timezone.utc)
    today = now.date().isoformat()
    day_ago = now - timedelta(hours=24)

    users_total = await db.users.count_documents({})
    active_students = await db.students.count_documents({'is_active': True})

    assignments_total = await db.assignments.count_documents({})
    submissions_total = await db.submissions.count_documents({})
    assignment_completion_pct = round((submissions_total / assignments_total) * 100, 2) if assignments_total else 0.0

    clubs_total = await db.clubs.count_documents({'status': {'$in': ['active', 'registration_closed']}})
    active_club_members = await db.club_members.count_documents({'status': 'active'})
    club_participation_pct = round((active_club_members / active_students) * 100, 2) if active_students else 0.0

    events_total = await db.club_events.count_documents({})
    event_registrations = await db.event_registrations.count_documents({'status': {'$in': ['registered', 'approved']}})
    event_attendance_pct = round((event_registrations / events_total) * 100, 2) if events_total else 0.0

    pending_tickets = await db.review_tickets.count_documents({'status': {'$in': ['pending', 'open']}})

    login_count_24h = await db.audit_logs.count_documents(
        {
            'action_type': 'login',
            'created_at': {'$gte': day_ago},
            'actor_user_id': {'$ne': None},
        }
    )
    daily_active_user_ids = await db.audit_logs.distinct(
        'actor_user_id',
        {
            'action_type': 'login',
            'created_at': {'$gte': day_ago},
            'actor_user_id': {'$ne': None},
        },
    )
    daily_active_users = len(daily_active_user_ids)

    sla_pipeline = [
        {'$match': {'status': {'$in': ['approved', 'rejected']}, 'resolved_at': {'$ne': None}}},
        {
            '$project': {
                'duration_hours': {
                    '$divide': [{'$subtract': ['$resolved_at', '$created_at']}, 3600000]
                }
            }
        },
        {'$group': {'_id': None, 'avg_hours': {'$avg': '$duration_hours'}}},
    ]
    sla_rows = await db.review_tickets.aggregate(sla_pipeline).to_list(length=1)
    review_ticket_sla_hours = round(float(sla_rows[0].get('avg_hours', 0.0)), 2) if sla_rows else 0.0

    snapshot = {
        'date': today,
        'users_total': users_total,
        'active_students': active_students,
        'daily_active_users': daily_active_users,
        'login_count_24h': login_count_24h,
        'assignment_completion_pct': assignment_completion_pct,
        'club_participation_pct': club_participation_pct,
        'event_attendance_pct': event_attendance_pct,
        'review_ticket_sla_hours': review_ticket_sla_hours,
        'pending_review_tickets': pending_tickets,
        'updated_at': now,
    }

    await db.platform_metrics.update_one({'date': today}, {'$set': snapshot}, upsert=True)

    return {
        'timestamp': datetime.now(timezone.utc),
        'metrics': snapshot,
    }


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
