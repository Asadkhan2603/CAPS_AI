from __future__ import annotations

import contextvars
import json
import logging
import math
import sys
from collections import deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Any
from uuid import uuid4

from app.core.config import settings


request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")
_REQUEST_WINDOW_MINUTES = 15
_MAX_REQUEST_EVENTS = 5000
_MAX_ALERTS = 10


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_error_id() -> str:
    return f"err_{uuid4().hex[:12]}"


def _serialize_dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _percentile(values: list[int], percentile: float) -> int | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(len(ordered) * percentile) - 1))
    return ordered[index]


class ObservabilityState:
    def __init__(self) -> None:
        self._lock = Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self._active_requests = 0
            self._request_total = 0
            self._request_events: deque[dict[str, Any]] = deque(maxlen=_MAX_REQUEST_EVENTS)
            self._leader_acquired_total = 0
            self._leader_lost_total = 0
            self._leader_election_errors_total = 0
            self._last_leader_acquired_at: datetime | None = None
            self._last_leader_lost_at: datetime | None = None
            self._last_leader_election_error_at: datetime | None = None
            self._scheduler_jobs: dict[str, dict[str, Any]] = {
                "notice_dispatch": self._new_scheduler_job_state(),
                "ai_jobs": self._new_scheduler_job_state(),
                "daily_snapshot": self._new_scheduler_job_state(),
            }

    def _new_scheduler_job_state(self) -> dict[str, Any]:
        return {
            "iterations_total": 0,
            "success_total": 0,
            "error_total": 0,
            "processed_total": 0,
            "last_duration_ms": None,
            "last_run_at": None,
            "last_success_at": None,
            "last_error_at": None,
            "last_processed_count": None,
        }

    def request_started(self) -> None:
        with self._lock:
            self._active_requests += 1

    def record_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_ms: int,
    ) -> None:
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)
            self._request_total += 1
            self._request_events.append(
                {
                    "timestamp": datetime.now(timezone.utc),
                    "method": method.upper(),
                    "path": path,
                    "status_code": int(status_code),
                    "duration_ms": max(0, int(duration_ms)),
                }
            )

    def record_scheduler_leadership(self, *, acquired: bool) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            if acquired:
                self._leader_acquired_total += 1
                self._last_leader_acquired_at = now
            else:
                self._leader_lost_total += 1
                self._last_leader_lost_at = now

    def record_scheduler_election_error(self) -> None:
        with self._lock:
            self._leader_election_errors_total += 1
            self._last_leader_election_error_at = datetime.now(timezone.utc)

    def record_scheduler_job_run(
        self,
        *,
        job_name: str,
        success: bool,
        duration_ms: int,
        processed_count: int | None = None,
    ) -> None:
        now = datetime.now(timezone.utc)
        with self._lock:
            job = self._scheduler_jobs.setdefault(job_name, self._new_scheduler_job_state())
            job["iterations_total"] += 1
            if success:
                job["success_total"] += 1
                job["last_success_at"] = now
            else:
                job["error_total"] += 1
                job["last_error_at"] = now
            job["last_run_at"] = now
            job["last_duration_ms"] = max(0, int(duration_ms))
            if processed_count is not None:
                job["last_processed_count"] = int(processed_count)
                job["processed_total"] += max(0, int(processed_count))

    def snapshot(self) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(minutes=_REQUEST_WINDOW_MINUTES)
        with self._lock:
            recent = [event for event in self._request_events if event["timestamp"] >= cutoff]
            durations = [int(event["duration_ms"]) for event in recent]
            slow_threshold_ms = settings.observability_slow_request_ms
            slow_requests = [event for event in recent if int(event["duration_ms"]) >= slow_threshold_ms]
            server_errors = [event for event in recent if int(event["status_code"]) >= 500]
            client_errors = [
                event for event in recent if 400 <= int(event["status_code"]) < 500
            ]

            by_path: dict[str, dict[str, Any]] = {}
            for event in recent:
                path = str(event["path"])
                item = by_path.setdefault(
                    path,
                    {
                        "path": path,
                        "requests": 0,
                        "server_errors": 0,
                        "slow_requests": 0,
                        "_durations": [],
                    },
                )
                item["requests"] += 1
                if int(event["status_code"]) >= 500:
                    item["server_errors"] += 1
                if int(event["duration_ms"]) >= slow_threshold_ms:
                    item["slow_requests"] += 1
                item["_durations"].append(int(event["duration_ms"]))

            top_paths = []
            for item in by_path.values():
                top_paths.append(
                    {
                        "path": item["path"],
                        "requests": item["requests"],
                        "server_errors": item["server_errors"],
                        "slow_requests": item["slow_requests"],
                        "avg_duration_ms": int(sum(item["_durations"]) / len(item["_durations"])),
                        "p95_duration_ms": _percentile(item["_durations"], 0.95),
                    }
                )
            top_paths.sort(key=lambda item: (-item["requests"], -item["avg_duration_ms"], item["path"]))

            scheduler_jobs = {}
            for job_name, job in self._scheduler_jobs.items():
                last_run_at = job["last_run_at"]
                scheduler_jobs[job_name] = {
                    "iterations_total": job["iterations_total"],
                    "success_total": job["success_total"],
                    "error_total": job["error_total"],
                    "processed_total": job["processed_total"],
                    "last_duration_ms": job["last_duration_ms"],
                    "last_processed_count": job["last_processed_count"],
                    "last_run_at": _serialize_dt(last_run_at),
                    "last_success_at": _serialize_dt(job["last_success_at"]),
                    "last_error_at": _serialize_dt(job["last_error_at"]),
                    "last_run_age_seconds": int((now - last_run_at).total_seconds()) if last_run_at else None,
                }

            request_metrics = {
                "window_minutes": _REQUEST_WINDOW_MINUTES,
                "active_requests": self._active_requests,
                "requests_total": self._request_total,
                "requests_15m": len(recent),
                "server_errors_15m": len(server_errors),
                "client_errors_15m": len(client_errors),
                "server_error_rate_pct_15m": round(
                    (len(server_errors) / len(recent)) * 100, 2
                )
                if recent
                else 0.0,
                "slow_request_threshold_ms": slow_threshold_ms,
                "slow_requests_15m": len(slow_requests),
                "avg_duration_ms_15m": int(sum(durations) / len(durations)) if durations else None,
                "p95_duration_ms_15m": _percentile(durations, 0.95),
                "top_paths_15m": top_paths[:5],
            }
            scheduler_metrics = {
                "leader_acquired_total": self._leader_acquired_total,
                "leader_lost_total": self._leader_lost_total,
                "leader_election_errors_total": self._leader_election_errors_total,
                "last_leader_acquired_at": _serialize_dt(self._last_leader_acquired_at),
                "last_leader_lost_at": _serialize_dt(self._last_leader_lost_at),
                "last_leader_election_error_at": _serialize_dt(self._last_leader_election_error_at),
                "jobs": scheduler_jobs,
            }
        return {
            "request_metrics": request_metrics,
            "scheduler_metrics": scheduler_metrics,
        }


def build_operational_alerts(
    *,
    db_status: str,
    scheduler_status: dict[str, Any],
    scheduler_lock: dict[str, Any] | None,
    snapshot: dict[str, Any],
) -> list[dict[str, Any]]:
    alerts: list[dict[str, Any]] = []
    now = datetime.now(timezone.utc)
    request_metrics = snapshot.get("request_metrics") or {}
    scheduler_metrics = snapshot.get("scheduler_metrics") or {}

    if db_status != "ok":
        alerts.append(
            {
                "level": "critical",
                "code": "db.unreachable",
                "message": "Database health check failed.",
            }
        )

    requests_15m = int(request_metrics.get("requests_15m") or 0)
    error_rate_15m = float(request_metrics.get("server_error_rate_pct_15m") or 0.0)
    if requests_15m > 0 and error_rate_15m >= settings.observability_error_rate_threshold_pct:
        alerts.append(
            {
                "level": "high",
                "code": "http.high_server_error_rate",
                "message": (
                    f"Server error rate is {error_rate_15m:.2f}% in the last "
                    f"{request_metrics.get('window_minutes') or _REQUEST_WINDOW_MINUTES} minutes."
                ),
            }
        )

    slow_requests_15m = int(request_metrics.get("slow_requests_15m") or 0)
    if slow_requests_15m >= settings.observability_slow_request_count_alert_threshold:
        alerts.append(
            {
                "level": "medium",
                "code": "http.slow_requests",
                "message": (
                    f"{slow_requests_15m} requests exceeded "
                    f"{request_metrics.get('slow_request_threshold_ms') or settings.observability_slow_request_ms} ms "
                    f"in the last {request_metrics.get('window_minutes') or _REQUEST_WINDOW_MINUTES} minutes."
                ),
            }
        )

    if scheduler_status.get("enabled"):
        if not scheduler_status.get("running"):
            alerts.append(
                {
                    "level": "high",
                    "code": "scheduler.not_running",
                    "message": "Scheduler is enabled but not running in this process.",
                }
            )
        else:
            expires_at = scheduler_lock.get("expires_at") if scheduler_lock else None
            if not expires_at or expires_at <= now:
                alerts.append(
                    {
                        "level": "high",
                        "code": "scheduler.leader_lock_missing",
                        "message": "No valid scheduler leader lock is currently held.",
                    }
                )

        election_errors = int(scheduler_metrics.get("leader_election_errors_total") or 0)
        if election_errors > 0:
            alerts.append(
                {
                    "level": "medium",
                    "code": "scheduler.leader_election_errors",
                    "message": f"Scheduler leader election has recorded {election_errors} errors.",
                }
            )

    return alerts[:_MAX_ALERTS]


observability_state = ObservabilityState()


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": _utc_now_iso(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get() or None,
            "trace_id": trace_id_ctx.get() or None,
        }
        if isinstance(record.msg, dict):
            payload.update(record.msg)
            payload["message"] = record.msg.get("event", payload["message"])
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Prevent duplicate handlers when app reloads in development.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(JsonFormatter())
    root_logger.addHandler(stream)
