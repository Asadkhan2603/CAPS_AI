from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.config import settings
from app.core.database import db
from app.schemas.user import (
    UsersAdminDashboardAlert,
    UsersAdminDashboardPageSize,
    UsersAdminDashboardResponse,
    UsersAdminLatencyDashboard,
    UsersAdminLatencyDashboardBucket,
    UsersAdminPaginationDashboard,
)


def _to_int(value: Any, default: int = 0) -> int:
    try:
        if value is None:
            return default
        return int(float(value))
    except Exception:
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        return float(value)
    except Exception:
        return default


def _percentile(values: list[int], percentile: float) -> int:
    if not values:
        return 0
    if len(values) == 1:
        return int(values[0])
    ordered = sorted(values)
    rank = ((len(ordered) - 1) * max(0.0, min(100.0, percentile))) / 100.0
    lower = math.floor(rank)
    upper = math.ceil(rank)
    if lower == upper:
        return int(ordered[lower])
    weight = rank - lower
    return int(round((ordered[lower] * (1.0 - weight)) + (ordered[upper] * weight)))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _floor_to_minute_bucket(value: datetime, bucket_minutes: int) -> datetime:
    normalized = value.astimezone(timezone.utc).replace(second=0, microsecond=0)
    minute = normalized.minute - (normalized.minute % max(1, int(bucket_minutes)))
    return normalized.replace(minute=minute)


def build_users_admin_alerts(dashboard: UsersAdminDashboardResponse) -> list[UsersAdminDashboardAlert]:
    alerts: list[UsersAdminDashboardAlert] = []
    error_rate = _to_float(dashboard.latency.error_rate_pct, 0.0)
    p95_latency = _to_float(dashboard.latency.p95_duration_ms, 0.0)
    empty_page_rate = _to_float(dashboard.pagination.empty_page_rate_pct, 0.0)
    deep_page_rate = _to_float(dashboard.pagination.deep_page_rate_pct, 0.0)

    warning_error_rate = float(settings.users_admin_alert_error_rate_warning_pct)
    critical_error_rate = float(settings.users_admin_alert_error_rate_critical_pct)
    warning_p95 = float(settings.users_admin_alert_p95_latency_warning_ms)
    critical_p95 = float(settings.users_admin_alert_p95_latency_critical_ms)
    warning_empty_page = float(settings.users_admin_alert_empty_page_warning_pct)
    warning_deep_page = float(settings.users_admin_alert_deep_page_warning_pct)

    if error_rate > critical_error_rate:
        alerts.append(
            UsersAdminDashboardAlert(
                code="users.admin.error_rate.critical",
                level="critical",
                metric="error_rate_pct",
                current_value=round(error_rate, 2),
                threshold_value=round(critical_error_rate, 2),
                comparison=">",
                message=(
                    f"Users admin list error rate is {error_rate:.2f}% "
                    f"(critical threshold {critical_error_rate:.2f}%)."
                ),
            )
        )
    elif error_rate > warning_error_rate:
        alerts.append(
            UsersAdminDashboardAlert(
                code="users.admin.error_rate.warning",
                level="warning",
                metric="error_rate_pct",
                current_value=round(error_rate, 2),
                threshold_value=round(warning_error_rate, 2),
                comparison=">",
                message=(
                    f"Users admin list error rate is {error_rate:.2f}% "
                    f"(warning threshold {warning_error_rate:.2f}%)."
                ),
            )
        )

    if p95_latency > critical_p95:
        alerts.append(
            UsersAdminDashboardAlert(
                code="users.admin.p95_latency.critical",
                level="critical",
                metric="p95_duration_ms",
                current_value=round(p95_latency, 2),
                threshold_value=round(critical_p95, 2),
                comparison=">",
                message=(
                    f"Users admin list p95 latency is {p95_latency:.0f}ms "
                    f"(critical threshold {critical_p95:.0f}ms)."
                ),
            )
        )
    elif p95_latency > warning_p95:
        alerts.append(
            UsersAdminDashboardAlert(
                code="users.admin.p95_latency.warning",
                level="warning",
                metric="p95_duration_ms",
                current_value=round(p95_latency, 2),
                threshold_value=round(warning_p95, 2),
                comparison=">",
                message=(
                    f"Users admin list p95 latency is {p95_latency:.0f}ms "
                    f"(warning threshold {warning_p95:.0f}ms)."
                ),
            )
        )

    if empty_page_rate > warning_empty_page:
        alerts.append(
            UsersAdminDashboardAlert(
                code="users.admin.empty_page_rate.warning",
                level="warning",
                metric="empty_page_rate_pct",
                current_value=round(empty_page_rate, 2),
                threshold_value=round(warning_empty_page, 2),
                comparison=">",
                message=(
                    f"Users admin empty-page rate is {empty_page_rate:.2f}% "
                    f"(warning threshold {warning_empty_page:.2f}%)."
                ),
            )
        )

    if deep_page_rate > warning_deep_page:
        alerts.append(
            UsersAdminDashboardAlert(
                code="users.admin.deep_page_rate.warning",
                level="warning",
                metric="deep_page_rate_pct",
                current_value=round(deep_page_rate, 2),
                threshold_value=round(warning_deep_page, 2),
                comparison=">",
                message=(
                    f"Users admin deep-page rate is {deep_page_rate:.2f}% "
                    f"(warning threshold {warning_deep_page:.2f}%)."
                ),
            )
        )

    return alerts


def users_admin_alerts_for_operational_routing(dashboard: UsersAdminDashboardResponse) -> list[dict[str, Any]]:
    return [
        {"code": item.code, "level": item.level, "message": item.message}
        for item in build_users_admin_alerts(dashboard)
    ]


async def build_users_admin_dashboard(
    *,
    window_minutes: int = 60,
    bucket_minutes: int = 5,
    database: Any = db,
) -> UsersAdminDashboardResponse:
    now = _utc_now()
    window_start = now - timedelta(minutes=max(5, int(window_minutes)))
    docs = (
        await database.users_admin_telemetry.find(
            {"event": "users.admin.list", "created_at": {"$gte": window_start}},
            {"_id": 0, "created_at": 1, "outcome": 1, "metadata": 1},
        )
        .sort("created_at", -1)
        .limit(5000)
        .to_list(length=5000)
    )

    request_count = len(docs)
    success_docs = [doc for doc in docs if str(doc.get("outcome")) == "success"]
    error_count = request_count - len(success_docs)

    durations: list[int] = []
    pages: list[int] = []
    limits: list[int] = []
    returned_counts: list[int] = []
    page_size_counts: dict[int, int] = {}
    bucket_map: dict[datetime, dict[str, Any]] = {}

    for doc in docs:
        metadata = doc.get("metadata")
        metadata = metadata if isinstance(metadata, dict) else {}
        created_at = doc.get("created_at")
        created_at = created_at if isinstance(created_at, datetime) else now
        bucket = _floor_to_minute_bucket(created_at, bucket_minutes)
        bucket_entry = bucket_map.setdefault(bucket, {"requests": 0, "errors": 0, "durations": []})
        bucket_entry["requests"] += 1

        is_success = str(doc.get("outcome")) == "success"
        if not is_success:
            bucket_entry["errors"] += 1

        duration_ms = _to_int(metadata.get("duration_ms"), default=-1)
        if duration_ms >= 0 and is_success:
            durations.append(duration_ms)
            bucket_entry["durations"].append(duration_ms)

        if not is_success:
            continue

        page = _to_int(metadata.get("page"), default=0)
        if page > 0:
            pages.append(page)

        limit = _to_int(metadata.get("limit"), default=0)
        if limit > 0:
            limits.append(limit)
            page_size_counts[limit] = page_size_counts.get(limit, 0) + 1

        returned = _to_int(metadata.get("returned"), default=-1)
        if returned >= 0:
            returned_counts.append(returned)

    avg_duration_ms = int(round(sum(durations) / len(durations))) if durations else 0
    error_rate_pct = round((error_count * 100.0 / request_count), 2) if request_count else 0.0
    avg_page = round(sum(pages) / len(pages), 2) if pages else 0.0
    avg_limit = round(sum(limits) / len(limits), 2) if limits else 0.0
    empty_page_rate_pct = (
        round((sum(1 for value in returned_counts if value == 0) * 100.0 / len(returned_counts)), 2)
        if returned_counts
        else 0.0
    )
    deep_page_rate_pct = (
        round((sum(1 for value in pages if value >= 5) * 100.0 / len(pages)), 2) if pages else 0.0
    )

    top_page_sizes = [
        UsersAdminDashboardPageSize(page_size=page_size, count=count)
        for page_size, count in sorted(page_size_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
    ]

    buckets = [
        UsersAdminLatencyDashboardBucket(
            bucket_start=bucket_start,
            requests=_to_int(values.get("requests")),
            errors=_to_int(values.get("errors")),
            avg_duration_ms=int(round(sum(values.get("durations", [])) / len(values.get("durations", []))))
            if values.get("durations")
            else 0,
            p95_duration_ms=_percentile(values.get("durations", []), 95.0),
        )
        for bucket_start, values in sorted(bucket_map.items(), key=lambda item: item[0])
    ]

    dashboard = UsersAdminDashboardResponse(
        window_minutes=max(5, int(window_minutes)),
        bucket_minutes=max(1, int(bucket_minutes)),
        generated_at=now,
        latency=UsersAdminLatencyDashboard(
            request_count=request_count,
            success_count=len(success_docs),
            error_count=error_count,
            error_rate_pct=error_rate_pct,
            avg_duration_ms=avg_duration_ms,
            p50_duration_ms=_percentile(durations, 50.0),
            p95_duration_ms=_percentile(durations, 95.0),
            p99_duration_ms=_percentile(durations, 99.0),
            buckets=buckets,
        ),
        pagination=UsersAdminPaginationDashboard(
            sample_count=len(success_docs),
            avg_page=avg_page,
            avg_limit=avg_limit,
            empty_page_rate_pct=empty_page_rate_pct,
            deep_page_rate_pct=deep_page_rate_pct,
            top_page_sizes=top_page_sizes,
        ),
    )
    dashboard.alerts = build_users_admin_alerts(dashboard)
    return dashboard
