import csv
import json
from datetime import datetime, timedelta, timezone
from io import StringIO
from typing import Any

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.security import require_permission
from app.schemas.communication_delivery import (
    CommunicationDeliveryAnomalyReportOut,
    CommunicationDeliveryBreakdownRowOut,
    CommunicationDeliveryEmailHealthOut,
    CommunicationDeliveryErrorSummaryOut,
    CommunicationDeliveryReportOut,
    CommunicationDeliveryTrendReportOut,
    DeliveryDetailsOut,
    DeliveryRetryEmailRequest,
    DeliveryRetryEmailResponse,
)
from app.services.club_permissions import can_manage_club
from app.services.communication_deliveries import get_delivery_rows, get_delivery_summaries
from app.services.communication_digests import dispatch_due_notification_digests, get_notification_digest_report
from app.services.communication_delivery_retry import retry_source_email_delivery
from app.services.public_ids import build_user_label

router = APIRouter()


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _parse_days(days: int) -> timedelta:
    return timedelta(days=max(1, min(days, 365)))


def _delivery_sort_key(item: dict) -> tuple[str, str, str]:
    target_label = str(item.get('target_user_label') or item.get('target_email') or item.get('target_user_id') or '').lower()
    channel = str(item.get('channel') or '').lower()
    status = str(item.get('status') or '').lower()
    return (target_label, channel, status)


def _normalize_datetime(value: Any) -> datetime | None:
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _bucket_start_for_day(value: datetime) -> datetime:
    normalized = _normalize_datetime(value) or _utcnow()
    return normalized.replace(hour=0, minute=0, second=0, microsecond=0)


async def _load_source_maps(rows: list[dict[str, Any]]) -> tuple[dict[str, dict], dict[str, dict]]:
    notice_ids = sorted(
        {row.get("source_id") for row in rows if row.get("source_kind") == "notice" and row.get("source_id")}
    )
    notification_ids = sorted(
        {row.get("source_id") for row in rows if row.get("source_kind") == "notification" and row.get("source_id")}
    )
    notices_by_id: dict[str, dict] = {}
    notifications_by_id: dict[str, dict] = {}
    if notice_ids:
        notice_docs = await db.notices.find({"_id": {"$in": [parse_object_id(value) for value in notice_ids]}}).to_list(length=len(notice_ids))
        notices_by_id = {str(item.get("_id")): item for item in notice_docs if item.get("_id")}
    if notification_ids:
        notification_docs = await db.notifications.find({"_id": {"$in": [parse_object_id(value) for value in notification_ids]}}).to_list(length=len(notification_ids))
        notifications_by_id = {str(item.get("_id")): item for item in notification_docs if item.get("_id")}
    return notices_by_id, notifications_by_id


def _source_context(
    *,
    row: dict[str, Any],
    notices_by_id: dict[str, dict],
    notifications_by_id: dict[str, dict],
) -> tuple[str, str | None]:
    kind = str(row.get("source_kind") or "").strip().lower()
    source_id = str(row.get("source_id") or "")
    source_doc = notifications_by_id.get(source_id) if kind == "notification" else notices_by_id.get(source_id)
    scope = str((source_doc or {}).get("scope") or "unknown")
    created_by = str((source_doc or {}).get("created_by") or "").strip() or None
    return scope, created_by


def _row_matches_report_filters(
    *,
    row: dict[str, Any],
    date_from: datetime | None,
    scope: str | None,
    status: str | None,
    created_by: str | None,
    notices_by_id: dict[str, dict],
    notifications_by_id: dict[str, dict],
) -> tuple[bool, str, str | None]:
    updated_at = _normalize_datetime(row.get("updated_at") or row.get("sent_at") or row.get("read_at"))
    if date_from and updated_at and updated_at < date_from:
        return False, "unknown", None
    row_status = str(row.get("status") or "pending").strip().lower()
    if status and row_status != status:
        return False, "unknown", None
    source_scope, source_created_by = _source_context(
        row=row,
        notices_by_id=notices_by_id,
        notifications_by_id=notifications_by_id,
    )
    if scope and source_scope != scope:
        return False, source_scope, source_created_by
    if created_by and source_created_by != created_by:
        return False, source_scope, source_created_by
    return True, source_scope, source_created_by


async def _serialize_delivery_details(*, source_kind: str, source_doc: dict) -> DeliveryDetailsOut:
    source_id = str(source_doc.get('_id'))
    rows = await get_delivery_rows(source_kind=source_kind, source_id=source_id)
    user_ids = [
        parse_object_id(str(row.get('target_user_id')))
        for row in rows
        if row.get('target_user_id') and ObjectId.is_valid(str(row.get('target_user_id')))
    ]
    users_by_id: dict[str, dict] = {}
    if user_ids:
        user_rows = await db.users.find({'_id': {'$in': user_ids}}).to_list(length=max(len(user_ids), 1))
        users_by_id = {str(item.get('_id')): item for item in user_rows if item.get('_id')}

    items = []
    for row in rows:
        target_user_id = str(row.get('target_user_id') or '').strip() or None
        target_user = users_by_id.get(target_user_id or '')
        items.append(
            {
                'target_user_id': target_user_id,
                'target_user_label': build_user_label(
                    target_user_id,
                    full_name=(target_user or {}).get('full_name') or row.get('target_user_name'),
                    email=(target_user or {}).get('email') or row.get('target_email'),
                ),
                'target_email': (target_user or {}).get('email') or row.get('target_email'),
                'channel': row.get('channel') or 'in_app',
                'status': row.get('status') or 'pending',
                'sent_at': row.get('sent_at'),
                'read_at': row.get('read_at'),
                'error': row.get('error'),
                'metadata': row.get('metadata') or {},
            }
        )

    items = sorted(items, key=_delivery_sort_key)
    summary_map = await get_delivery_summaries(source_kind=source_kind, source_ids=[source_id])
    return DeliveryDetailsOut(
        source_kind=source_kind,
        source_id=source_id,
        source_public_id=source_doc.get('public_id'),
        source_title=source_doc.get('title'),
        summary=summary_map.get(source_id) or {},
        items=items,
    )


def _format_csv_value(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _new_breakdown_bucket(*, key: str, label: str) -> dict[str, Any]:
    return {
        "key": key,
        "label": label,
        "total_count": 0,
        "sent_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "pending_count": 0,
        "read_count": 0,
    }


def _apply_delivery_status_counts(*, bucket: dict[str, Any], row: dict[str, Any]) -> None:
    bucket["total_count"] = int(bucket.get("total_count") or 0) + 1
    normalized_status = str(row.get("status") or "pending").strip().lower()
    if normalized_status in {"sent", "read"}:
        bucket["sent_count"] = int(bucket.get("sent_count") or 0) + 1
    elif normalized_status == "failed":
        bucket["failed_count"] = int(bucket.get("failed_count") or 0) + 1
    elif normalized_status == "skipped":
        bucket["skipped_count"] = int(bucket.get("skipped_count") or 0) + 1
    else:
        bucket["pending_count"] = int(bucket.get("pending_count") or 0) + 1
    if normalized_status == "read" or row.get("read_at"):
        bucket["read_count"] = int(bucket.get("read_count") or 0) + 1


def _finalize_breakdown_rows(buckets: dict[str, dict[str, Any]], *, limit: int = 8) -> list[CommunicationDeliveryBreakdownRowOut]:
    rows: list[CommunicationDeliveryBreakdownRowOut] = []
    for item in buckets.values():
        total = max(1, int(item.get("total_count") or 0))
        rows.append(
            CommunicationDeliveryBreakdownRowOut(
                key=str(item.get("key") or "unknown"),
                label=str(item.get("label") or item.get("key") or "Unknown"),
                total_count=int(item.get("total_count") or 0),
                sent_count=int(item.get("sent_count") or 0),
                failed_count=int(item.get("failed_count") or 0),
                skipped_count=int(item.get("skipped_count") or 0),
                pending_count=int(item.get("pending_count") or 0),
                read_count=int(item.get("read_count") or 0),
                failed_rate_pct=round((float(item.get("failed_count") or 0) / float(total)) * 100.0, 2),
                pending_rate_pct=round((float(item.get("pending_count") or 0) / float(total)) * 100.0, 2),
                read_rate_pct=round((float(item.get("read_count") or 0) / float(total)) * 100.0, 2),
            )
        )
    rows.sort(key=lambda item: (-item.total_count, -item.failed_count, item.label.lower()))
    return rows[:limit]


def _build_csv_response(*, rows: list[dict[str, Any]], fieldnames: list[str], filename: str) -> Response:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({field: _format_csv_value(row.get(field)) for field in fieldnames})
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def _delivery_rows_for_export(*, source_kind: str, source_doc: dict) -> list[dict[str, Any]]:
    details = await _serialize_delivery_details(source_kind=source_kind, source_doc=source_doc)
    rows: list[dict[str, Any]] = []
    for item in details.items:
        payload = item.model_dump()
        payload["source_kind"] = details.source_kind
        payload["source_public_id"] = details.source_public_id
        payload["source_title"] = details.source_title
        payload["source_scope"] = source_doc.get("scope")
        payload["source_created_by"] = source_doc.get("created_by")
        rows.append(payload)
    return rows


async def _delivery_report(
    *,
    date_from: datetime | None,
    source_kind: str | None = None,
    scope: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
) -> CommunicationDeliveryReportOut:
    query: dict[str, Any] = {}
    if source_kind:
        query["source_kind"] = source_kind
    rows = await db.communication_deliveries.find(query).to_list(length=20000)
    filtered_rows: list[dict[str, Any]] = []
    creator_buckets: dict[str, dict[str, Any]] = {}
    scope_buckets: dict[str, dict[str, Any]] = {}
    email_bucket = _new_breakdown_bucket(key="email", label="Email")
    email_errors: dict[str, int] = {}
    report = {
        "total_rows": 0,
        "total_sources": 0,
        "sent_count": 0,
        "failed_count": 0,
        "skipped_count": 0,
        "pending_count": 0,
        "read_count": 0,
        "by_channel": {},
        "by_status": {},
        "by_source_kind": {},
        "by_scope": {},
        "digest": await get_notification_digest_report(),
        "creator_rows": [],
        "scope_rows": [],
        "email_health": CommunicationDeliveryEmailHealthOut(),
    }
    notices_by_id, notifications_by_id = await _load_source_maps(rows)

    for row in rows:
        matched, source_scope, source_created_by = _row_matches_report_filters(
            row=row,
            date_from=date_from,
            scope=scope,
            status=status,
            created_by=created_by,
            notices_by_id=notices_by_id,
            notifications_by_id=notifications_by_id,
        )
        if not matched:
            continue
        filtered_rows.append(row)

        report["total_rows"] += 1
        channel = str(row.get("channel") or "unknown").strip().lower()
        row_status = str(row.get("status") or "pending").strip().lower()
        kind = str(row.get("source_kind") or "unknown").strip().lower()
        report["by_channel"][channel] = int(report["by_channel"].get(channel) or 0) + 1
        report["by_status"][row_status] = int(report["by_status"].get(row_status) or 0) + 1
        report["by_source_kind"][kind] = int(report["by_source_kind"].get(kind) or 0) + 1
        if row_status in {"sent", "read"}:
            report["sent_count"] += 1
        elif row_status == "failed":
            report["failed_count"] += 1
        elif row_status == "skipped":
            report["skipped_count"] += 1
        else:
            report["pending_count"] += 1
        if row_status == "read" or row.get("read_at"):
            report["read_count"] += 1

        report["by_scope"][source_scope] = int(report["by_scope"].get(source_scope) or 0) + 1
        creator_key = str(source_created_by or "unknown")
        creator_bucket = creator_buckets.setdefault(
            creator_key,
            _new_breakdown_bucket(key=creator_key, label=creator_key if creator_key != "unknown" else "Unknown creator"),
        )
        scope_bucket = scope_buckets.setdefault(
            source_scope,
            _new_breakdown_bucket(key=source_scope, label=source_scope.replace("_", " ").title() if source_scope else "Unknown scope"),
        )
        _apply_delivery_status_counts(bucket=creator_bucket, row=row)
        _apply_delivery_status_counts(bucket=scope_bucket, row=row)

        channel = str(row.get("channel") or "unknown").strip().lower()
        if channel == "email":
            _apply_delivery_status_counts(bucket=email_bucket, row=row)
            error_message = str(row.get("error") or "").strip()
            if error_message:
                email_errors[error_message] = int(email_errors.get(error_message) or 0) + 1

    report["total_sources"] = len(
        {f"{row.get('source_kind')}:{row.get('source_id')}" for row in filtered_rows if row.get("source_id")}
    )
    report["creator_rows"] = _finalize_breakdown_rows(creator_buckets)
    report["scope_rows"] = _finalize_breakdown_rows(scope_buckets)
    email_total = max(1, int(email_bucket.get("total_count") or 0))
    report["email_health"] = CommunicationDeliveryEmailHealthOut(
        total_rows=int(email_bucket.get("total_count") or 0),
        sent_count=int(email_bucket.get("sent_count") or 0),
        failed_count=int(email_bucket.get("failed_count") or 0),
        skipped_count=int(email_bucket.get("skipped_count") or 0),
        pending_count=int(email_bucket.get("pending_count") or 0),
        read_count=int(email_bucket.get("read_count") or 0),
        delivered_rate_pct=round((float(email_bucket.get("sent_count") or 0) / float(email_total)) * 100.0, 2)
        if int(email_bucket.get("total_count") or 0) > 0
        else 0.0,
        attention_rate_pct=round(
            (
                float(email_bucket.get("failed_count") or 0)
                + float(email_bucket.get("skipped_count") or 0)
                + float(email_bucket.get("pending_count") or 0)
            )
            / float(email_total)
            * 100.0,
            2,
        )
        if int(email_bucket.get("total_count") or 0) > 0
        else 0.0,
        retry_candidate_count=int(email_bucket.get("failed_count") or 0) + int(email_bucket.get("skipped_count") or 0),
        top_errors=[
            CommunicationDeliveryErrorSummaryOut(error=error, count=count)
            for error, count in sorted(email_errors.items(), key=lambda item: (-item[1], item[0].lower()))[:5]
        ],
    )
    return CommunicationDeliveryReportOut(**report)


async def _delivery_trends(
    *,
    days: int,
    source_kind: str | None = None,
    scope: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
) -> CommunicationDeliveryTrendReportOut:
    safe_days = max(1, min(days, 365))
    date_from = _utcnow() - _parse_days(safe_days)
    query: dict[str, Any] = {}
    if source_kind:
        query["source_kind"] = source_kind
    rows = await db.communication_deliveries.find(query).to_list(length=20000)
    notices_by_id, notifications_by_id = await _load_source_maps(rows)

    points_by_bucket: dict[datetime, dict[str, Any]] = {}
    for offset in range(safe_days - 1, -1, -1):
        bucket = _bucket_start_for_day(_utcnow() - timedelta(days=offset))
        points_by_bucket[bucket] = {
            "bucket_start": bucket,
            "label": bucket.strftime("%b %d"),
            "total_count": 0,
            "sent_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "pending_count": 0,
            "read_count": 0,
        }

    for row in rows:
        matched, _source_scope, _source_created_by = _row_matches_report_filters(
            row=row,
            date_from=date_from,
            scope=scope,
            status=status,
            created_by=created_by,
            notices_by_id=notices_by_id,
            notifications_by_id=notifications_by_id,
        )
        if not matched:
            continue
        event_at = _normalize_datetime(row.get("updated_at") or row.get("sent_at") or row.get("read_at"))
        if event_at is None:
            continue
        bucket = _bucket_start_for_day(event_at)
        if bucket not in points_by_bucket:
            continue
        point = points_by_bucket[bucket]
        point["total_count"] += 1
        normalized_status = str(row.get("status") or "pending").strip().lower()
        if normalized_status in {"sent", "read"}:
            point["sent_count"] += 1
        elif normalized_status == "failed":
            point["failed_count"] += 1
        elif normalized_status == "skipped":
            point["skipped_count"] += 1
        else:
            point["pending_count"] += 1
        if normalized_status == "read" or row.get("read_at"):
            point["read_count"] += 1

    ordered_points = [points_by_bucket[key] for key in sorted(points_by_bucket.keys())]
    return CommunicationDeliveryTrendReportOut(granularity="day", days=safe_days, points=ordered_points)


def _average(values: list[float | int]) -> float:
    if not values:
        return 0.0
    return float(sum(values) / len(values))


async def _delivery_anomalies(
    *,
    days: int,
    source_kind: str | None = None,
    scope: str | None = None,
    status: str | None = None,
    created_by: str | None = None,
) -> CommunicationDeliveryAnomalyReportOut:
    trend_report = await _delivery_trends(
        days=days,
        source_kind=source_kind,
        scope=scope,
        status=status,
        created_by=created_by,
    )
    points = trend_report.points
    if not points:
        return CommunicationDeliveryAnomalyReportOut(days=days, alerts=[])

    latest = points[-1]
    history = points[:-1]
    recent_points = points[-3:] if len(points) >= 3 else points
    alerts: list[dict[str, Any]] = []

    latest_total = int(latest.total_count or 0)
    latest_failed = int(latest.failed_count or 0)
    latest_pending = int(latest.pending_count or 0)
    latest_skipped = int(latest.skipped_count or 0)
    latest_read = int(latest.read_count or 0)
    latest_sent = int(latest.sent_count or 0)

    baseline_failed_rate = _average(
        [
            (float(point.failed_count) / float(point.total_count)) * 100.0
            for point in history
            if int(point.total_count or 0) > 0
        ]
    )
    latest_failed_rate = (float(latest_failed) / float(latest_total)) * 100.0 if latest_total > 0 else 0.0
    if latest_failed >= 3 and latest_failed_rate >= max(20.0, baseline_failed_rate * 1.5 if baseline_failed_rate > 0 else 20.0):
        alerts.append(
            {
                "level": "critical" if latest_failed_rate >= 50.0 else "warning",
                "code": "delivery.failed_rate_spike",
                "message": (
                    f"Failed delivery rate reached {latest_failed_rate:.1f}% in the latest bucket"
                    + (
                        f", up from a {baseline_failed_rate:.1f}% historical average."
                        if baseline_failed_rate > 0
                        else "."
                    )
                ),
                "metric": "failed_rate_pct",
                "current_value": round(latest_failed_rate, 2),
                "baseline_value": round(baseline_failed_rate, 2),
            }
        )

    pending_series = [int(point.pending_count or 0) for point in recent_points]
    if len(pending_series) >= 3 and pending_series[0] < pending_series[1] < pending_series[2] and pending_series[-1] >= 3:
        alerts.append(
            {
                "level": "critical" if pending_series[-1] >= 10 else "warning",
                "code": "delivery.pending_backlog_rising",
                "message": f"Pending delivery rows have increased for {len(pending_series)} consecutive buckets, reaching {pending_series[-1]} in the latest bucket.",
                "metric": "pending_count",
                "current_value": pending_series[-1],
                "baseline_value": pending_series[0],
            }
        )

    baseline_skipped = _average([int(point.skipped_count or 0) for point in history])
    if latest_skipped >= max(5, int(baseline_skipped * 2) if baseline_skipped > 0 else 5):
        alerts.append(
            {
                "level": "warning",
                "code": "delivery.skipped_rows_high",
                "message": f"Skipped delivery rows reached {latest_skipped} in the latest bucket, which is above the recent baseline.",
                "metric": "skipped_count",
                "current_value": latest_skipped,
                "baseline_value": round(baseline_skipped, 2),
            }
        )

    if latest_total >= 5 and latest_sent == 0 and latest_read == 0:
        alerts.append(
            {
                "level": "warning",
                "code": "delivery.no_successful_progress",
                "message": "Latest delivery bucket shows activity but no sent or read progress.",
                "metric": "successful_progress_count",
                "current_value": 0,
                "baseline_value": latest_total,
            }
        )

    return CommunicationDeliveryAnomalyReportOut(days=days, alerts=alerts[:5])


async def _assert_notice_delivery_access(current_user: dict, notice: dict) -> None:
    if current_user.get('role') == 'admin':
        return
    if notice.get('created_by') == str(current_user.get('_id')):
        return
    if notice.get('scope') == 'club' and notice.get('scope_ref_id'):
        club = await db.clubs.find_one({'_id': parse_object_id(notice.get('scope_ref_id'))})
        if club and can_manage_club(current_user, club):
            return
    raise HTTPException(status_code=403, detail='Not allowed to inspect this notice delivery')


async def _assert_notification_delivery_access(current_user: dict, notification: dict) -> None:
    if current_user.get('role') == 'admin':
        return
    if notification.get('created_by') == str(current_user.get('_id')):
        return
    raise HTTPException(status_code=403, detail='Not allowed to inspect this notification delivery')


@router.post('/preview-target')
async def preview_target(
    payload: dict,
    _current_user=Depends(require_permission('announcements.publish')),
) -> dict:
    scope = (payload.get('scope') or 'college').strip().lower()
    scope_ref_id = payload.get('scope_ref_id')

    if scope in {'section', 'class'}:
        scope = 'class'

    if scope == 'college':
        matched_users = await db.users.count_documents({'is_active': True})
        return {'scope': 'college', 'matched_users': matched_users, 'estimated_reach': matched_users}

    if not scope_ref_id:
        raise HTTPException(status_code=400, detail='scope_ref_id is required for selected scope')

    if scope == 'batch':
        class_ids = [str(item) for item in await db.classes.distinct('_id', {'batch_id': scope_ref_id, 'is_active': True}) if item]
        student_ids: set[str] = set()
        if class_ids:
            student_ids = {
                value
                for value in await db.enrollments.distinct('student_id', {'class_id': {'$in': class_ids}})
                if isinstance(value, str) and value
            }
        return {'scope': 'batch', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    if scope == 'class':
        parse_object_id(scope_ref_id)
        student_ids = {
            value
            for value in await db.enrollments.distinct('student_id', {'class_id': scope_ref_id})
            if isinstance(value, str) and value
        }
        return {'scope': 'class', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    if scope == 'subject':
        parse_object_id(scope_ref_id)
        class_ids = {
            value
            for value in await db.assignments.distinct('class_id', {'subject_id': scope_ref_id})
            if isinstance(value, str) and value
        }
        student_ids: set[str] = set()
        if class_ids:
            student_ids = {
                value
                for value in await db.enrollments.distinct('student_id', {'class_id': {'$in': list(class_ids)}})
                if isinstance(value, str) and value
            }
        return {'scope': 'subject', 'matched_users': len(student_ids), 'estimated_reach': len(student_ids)}

    raise HTTPException(status_code=400, detail='Unsupported scope')


@router.get('/delivery/notices/{notice_id}', response_model=DeliveryDetailsOut)
async def get_notice_delivery_details(
    notice_id: str,
    current_user=Depends(require_permission('announcements.publish')),
) -> DeliveryDetailsOut:
    notice = await db.notices.find_one({'_id': parse_object_id(notice_id), 'is_active': True})
    if not notice:
        raise HTTPException(status_code=404, detail='Notice not found')
    await _assert_notice_delivery_access(current_user, notice)
    return await _serialize_delivery_details(source_kind='notice', source_doc=notice)


@router.get('/delivery/notifications/{notification_id}', response_model=DeliveryDetailsOut)
async def get_notification_delivery_details(
    notification_id: str,
    current_user=Depends(require_permission('announcements.publish')),
) -> DeliveryDetailsOut:
    notification = await db.notifications.find_one({'_id': parse_object_id(notification_id)})
    if not notification:
        raise HTTPException(status_code=404, detail='Notification not found')
    await _assert_notification_delivery_access(current_user, notification)
    return await _serialize_delivery_details(source_kind='notification', source_doc=notification)


@router.post('/delivery/notices/{notice_id}/retry-email', response_model=DeliveryRetryEmailResponse)
async def retry_notice_delivery_email(
    notice_id: str,
    payload: DeliveryRetryEmailRequest | None = None,
    current_user=Depends(require_permission('announcements.publish')),
) -> DeliveryRetryEmailResponse:
    notice = await db.notices.find_one({'_id': parse_object_id(notice_id), 'is_active': True})
    if not notice:
        raise HTTPException(status_code=404, detail='Notice not found')
    await _assert_notice_delivery_access(current_user, notice)
    request_payload = payload or DeliveryRetryEmailRequest()
    retried_count = await retry_source_email_delivery(
        source_kind='notice',
        source_doc=notice,
        target_user_ids=request_payload.target_user_ids,
        target_emails=request_payload.target_emails,
        include_skipped=request_payload.include_skipped,
    )
    refreshed = await db.notices.find_one({'_id': notice['_id']})
    return DeliveryRetryEmailResponse(
        retried_count=retried_count,
        details=await _serialize_delivery_details(source_kind='notice', source_doc=refreshed or notice),
    )


@router.post('/delivery/notifications/{notification_id}/retry-email', response_model=DeliveryRetryEmailResponse)
async def retry_notification_delivery_email(
    notification_id: str,
    payload: DeliveryRetryEmailRequest | None = None,
    current_user=Depends(require_permission('announcements.publish')),
) -> DeliveryRetryEmailResponse:
    notification = await db.notifications.find_one({'_id': parse_object_id(notification_id)})
    if not notification:
        raise HTTPException(status_code=404, detail='Notification not found')
    await _assert_notification_delivery_access(current_user, notification)
    request_payload = payload or DeliveryRetryEmailRequest()
    retried_count = await retry_source_email_delivery(
        source_kind='notification',
        source_doc=notification,
        target_user_ids=request_payload.target_user_ids,
        target_emails=request_payload.target_emails,
        include_skipped=request_payload.include_skipped,
    )
    refreshed = await db.notifications.find_one({'_id': notification['_id']})
    return DeliveryRetryEmailResponse(
        retried_count=retried_count,
        details=await _serialize_delivery_details(source_kind='notification', source_doc=refreshed or notification),
    )


@router.get('/delivery/notices/{notice_id}/export')
async def export_notice_delivery_csv(
    notice_id: str,
    current_user=Depends(require_permission('announcements.publish')),
) -> Response:
    notice = await db.notices.find_one({'_id': parse_object_id(notice_id), 'is_active': True})
    if not notice:
        raise HTTPException(status_code=404, detail='Notice not found')
    await _assert_notice_delivery_access(current_user, notice)
    rows = await _delivery_rows_for_export(source_kind='notice', source_doc=notice)
    filename = f"{notice.get('public_id') or notice_id}-delivery.csv"
    return _build_csv_response(
        rows=rows,
        fieldnames=['source_kind', 'source_public_id', 'source_title', 'source_scope', 'source_created_by', 'target_user_id', 'target_user_label', 'target_email', 'channel', 'status', 'sent_at', 'read_at', 'error', 'metadata'],
        filename=filename,
    )


@router.get('/delivery/notifications/{notification_id}/export')
async def export_notification_delivery_csv(
    notification_id: str,
    current_user=Depends(require_permission('announcements.publish')),
) -> Response:
    notification = await db.notifications.find_one({'_id': parse_object_id(notification_id)})
    if not notification:
        raise HTTPException(status_code=404, detail='Notification not found')
    await _assert_notification_delivery_access(current_user, notification)
    rows = await _delivery_rows_for_export(source_kind='notification', source_doc=notification)
    filename = f"{notification.get('public_id') or notification_id}-delivery.csv"
    return _build_csv_response(
        rows=rows,
        fieldnames=['source_kind', 'source_public_id', 'source_title', 'source_scope', 'source_created_by', 'target_user_id', 'target_user_label', 'target_email', 'channel', 'status', 'sent_at', 'read_at', 'error', 'metadata'],
        filename=filename,
    )


@router.get('/delivery/report', response_model=CommunicationDeliveryReportOut)
async def get_delivery_report(
    days: int = Query(default=7, ge=1, le=365),
    source_kind: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    status: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    _current_user=Depends(require_permission('announcements.publish')),
) -> CommunicationDeliveryReportOut:
    date_from = _utcnow() - _parse_days(days)
    return await _delivery_report(
        date_from=date_from,
        source_kind=source_kind,
        scope=(scope or None),
        status=(status or None),
        created_by=(created_by or None),
    )


@router.get('/delivery/report/trends', response_model=CommunicationDeliveryTrendReportOut)
async def get_delivery_report_trends(
    days: int = Query(default=7, ge=1, le=365),
    source_kind: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    status: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    _current_user=Depends(require_permission('announcements.publish')),
) -> CommunicationDeliveryTrendReportOut:
    return await _delivery_trends(
        days=days,
        source_kind=source_kind,
        scope=(scope or None),
        status=(status or None),
        created_by=(created_by or None),
    )


@router.get('/delivery/report/anomalies', response_model=CommunicationDeliveryAnomalyReportOut)
async def get_delivery_report_anomalies(
    days: int = Query(default=7, ge=1, le=365),
    source_kind: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    status: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    _current_user=Depends(require_permission('announcements.publish')),
) -> CommunicationDeliveryAnomalyReportOut:
    return await _delivery_anomalies(
        days=days,
        source_kind=source_kind,
        scope=(scope or None),
        status=(status or None),
        created_by=(created_by or None),
    )


@router.get('/delivery/report/export')
async def export_delivery_report_csv(
    days: int = Query(default=7, ge=1, le=365),
    source_kind: str | None = Query(default=None),
    scope: str | None = Query(default=None),
    status: str | None = Query(default=None),
    created_by: str | None = Query(default=None),
    view: str = Query(default="rows"),
    _current_user=Depends(require_permission('announcements.publish')),
) -> Response:
    date_from = _utcnow() - _parse_days(days)
    normalized_view = str(view or "rows").strip().lower()
    report = await _delivery_report(
        date_from=date_from,
        source_kind=source_kind,
        scope=(scope or None),
        status=(status or None),
        created_by=(created_by or None),
    )
    if normalized_view == "creator_summary":
        rows = [item.model_dump() for item in report.creator_rows]
        return _build_csv_response(
            rows=rows,
            fieldnames=["key", "label", "total_count", "sent_count", "failed_count", "skipped_count", "pending_count", "read_count", "failed_rate_pct", "pending_rate_pct", "read_rate_pct"],
            filename=f"communication-delivery-creators-{source_kind or 'all'}-{days}d.csv",
        )
    if normalized_view == "scope_summary":
        rows = [item.model_dump() for item in report.scope_rows]
        return _build_csv_response(
            rows=rows,
            fieldnames=["key", "label", "total_count", "sent_count", "failed_count", "skipped_count", "pending_count", "read_count", "failed_rate_pct", "pending_rate_pct", "read_rate_pct"],
            filename=f"communication-delivery-scopes-{source_kind or 'all'}-{days}d.csv",
        )
    if normalized_view == "email_health":
        rows = [
            {"section": "summary", "key": "total_rows", "value": report.email_health.total_rows},
            {"section": "summary", "key": "sent_count", "value": report.email_health.sent_count},
            {"section": "summary", "key": "failed_count", "value": report.email_health.failed_count},
            {"section": "summary", "key": "skipped_count", "value": report.email_health.skipped_count},
            {"section": "summary", "key": "pending_count", "value": report.email_health.pending_count},
            {"section": "summary", "key": "read_count", "value": report.email_health.read_count},
            {"section": "summary", "key": "delivered_rate_pct", "value": report.email_health.delivered_rate_pct},
            {"section": "summary", "key": "attention_rate_pct", "value": report.email_health.attention_rate_pct},
            {"section": "summary", "key": "retry_candidate_count", "value": report.email_health.retry_candidate_count},
            {"section": "digest", "key": "queued_total", "value": report.digest.get("queued_total", 0)},
            {"section": "digest", "key": "sent_total", "value": report.digest.get("sent_total", 0)},
            {"section": "digest", "key": "failed_total", "value": report.digest.get("failed_total", 0)},
        ]
        rows.extend(
            {"section": "top_error", "key": item.error, "value": item.count}
            for item in report.email_health.top_errors
        )
        return _build_csv_response(
            rows=rows,
            fieldnames=["section", "key", "value"],
            filename=f"communication-delivery-email-health-{source_kind or 'all'}-{days}d.csv",
        )
    if normalized_view != "rows":
        raise HTTPException(status_code=400, detail="Unsupported export view")

    query: dict[str, Any] = {}
    if source_kind:
        query['source_kind'] = source_kind
    rows = await db.communication_deliveries.find(query).to_list(length=20000)
    notices_by_id, notifications_by_id = await _load_source_maps(rows)
    export_rows = []
    for row in rows:
        matched, source_scope, source_created_by = _row_matches_report_filters(
            row=row,
            date_from=date_from,
            scope=(scope or None),
            status=(status or None),
            created_by=(created_by or None),
            notices_by_id=notices_by_id,
            notifications_by_id=notifications_by_id,
        )
        if not matched:
            continue
        source_doc = notifications_by_id.get(str(row.get('source_id'))) if row.get('source_kind') == 'notification' else notices_by_id.get(str(row.get('source_id')))
        export_rows.append(
            {
                'source_kind': row.get('source_kind'),
                'source_id': row.get('source_id'),
                'source_public_id': row.get('source_public_id'),
                'source_title': (source_doc or {}).get('title'),
                'source_scope': source_scope,
                'source_created_by': source_created_by,
                'target_user_id': row.get('target_user_id'),
                'target_email': row.get('target_email'),
                'channel': row.get('channel'),
                'status': row.get('status'),
                'sent_at': row.get('sent_at'),
                'read_at': row.get('read_at'),
                'updated_at': row.get('updated_at'),
                'error': row.get('error'),
                'metadata': row.get('metadata') or {},
            }
        )
    filename = f"communication-delivery-report-{source_kind or 'all'}-{days}d.csv"
    return _build_csv_response(
        rows=export_rows,
        fieldnames=['source_kind', 'source_id', 'source_public_id', 'source_title', 'source_scope', 'source_created_by', 'target_user_id', 'target_email', 'channel', 'status', 'sent_at', 'read_at', 'updated_at', 'error', 'metadata'],
        filename=filename,
    )


@router.post('/digests/process')
async def process_due_digests(
    limit: int = Query(default=200, ge=1, le=1000),
    _current_user=Depends(require_permission('announcements.publish')),
) -> dict[str, int]:
    return {'processed_count': await dispatch_due_notification_digests(limit=limit)}
