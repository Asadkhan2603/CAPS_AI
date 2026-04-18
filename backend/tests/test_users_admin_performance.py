from __future__ import annotations

import math
import time
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import settings
from tests.test_auth import FakeUsersCollection, _register_and_login, _setup_fake_db


def _ensure_users_admin_collections(fake_db) -> None:
    if not hasattr(fake_db, "users_admin_telemetry"):
        fake_db.users_admin_telemetry = FakeUsersCollection()
    if not hasattr(fake_db, "user_filter_presets"):
        fake_db.user_filter_presets = FakeUsersCollection()
    if not hasattr(fake_db, "user_invitations"):
        fake_db.user_invitations = FakeUsersCollection()
    if not hasattr(fake_db, "user_permission_templates"):
        fake_db.user_permission_templates = FakeUsersCollection()


def _p95(values: list[float]) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return float(ordered[index])


def _seed_users(fake_db, count: int) -> None:
    now = datetime.now(timezone.utc)
    for index in range(count):
        fake_db.users.items.append(
            {
                "_id": ObjectId(),
                "full_name": f"Perf User {index}",
                "email": f"perf.user{index}@example.com",
                "hashed_password": "hashed",
                "role": "teacher" if index % 2 == 0 else "student",
                "admin_type": None,
                "is_active": True,
                "extended_roles": ["year_head"] if index % 4 == 0 else [],
                "profile": {
                    "department": "Engineering" if index % 3 == 0 else "Science",
                    "designation": "Lecturer" if index % 2 == 0 else "Student",
                },
                "created_at": now - timedelta(days=(index % 365)),
                "updated_at": now - timedelta(minutes=index % 1440),
                "last_active_at": now - timedelta(minutes=index % 240),
            }
        )


def test_users_admin_list_p95_under_target_for_10k_dataset() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Admin Performance",
        email="admin.performance@example.com",
        role="admin",
    )
    _seed_users(fake_db, 10_000)

    durations_ms: list[float] = []
    for page in range(1, 21):
        started = time.perf_counter()
        response = client.get(
            "/api/v1/users/admin/list",
            params={"page": page, "limit": 50, "sort_by": "updated_at", "sort_dir": "desc"},
            headers=headers,
        )
        elapsed = (time.perf_counter() - started) * 1000
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload["limit"] == 50
        assert payload["total"] >= 10_000
        durations_ms.append(elapsed)

    # Target: keep request p95 for 10k+ rows below 1200ms in test environment.
    assert _p95(durations_ms) < 1200


def test_users_admin_dashboard_reports_latency_percentiles() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Admin Dashboard Perf",
        email="admin.dashboard-perf@example.com",
        role="admin",
    )

    now = datetime.now(timezone.utc)
    for index in range(120):
        fake_db.users_admin_telemetry.items.append(
            {
                "event": "users.admin.list",
                "outcome": "success",
                "scope": "workspace",
                "severity": "low",
                "actor_user_id": "admin-id",
                "created_at": now - timedelta(minutes=index % 30),
                "metadata": {
                    "duration_ms": 100 + (index % 50),
                    "page": (index % 8) + 1,
                    "limit": 25 if index % 2 == 0 else 50,
                    "returned": 25,
                    "total": 10000,
                },
            }
        )
    for index in range(6):
        fake_db.users_admin_telemetry.items.append(
            {
                "event": "users.admin.list",
                "outcome": "error",
                "scope": "workspace",
                "severity": "medium",
                "actor_user_id": "admin-id",
                "created_at": now - timedelta(minutes=index),
                "metadata": {"duration_ms": 500},
            }
        )

    response = client.get("/api/v1/users/admin/dashboard", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["latency"]["request_count"] >= 120
    assert payload["latency"]["p95_duration_ms"] > 0
    assert payload["pagination"]["sample_count"] >= 120
    assert len(payload["pagination"]["top_page_sizes"]) >= 1


def test_users_admin_dashboard_includes_threshold_alerts() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Admin Dashboard Alerts",
        email="admin.dashboard-alerts@example.com",
        role="admin",
    )

    now = datetime.now(timezone.utc)
    for _index in range(12):
        fake_db.users_admin_telemetry.items.append(
            {
                "event": "users.admin.list",
                "outcome": "error",
                "scope": "workspace",
                "severity": "medium",
                "actor_user_id": "admin-id",
                "created_at": now - timedelta(minutes=3),
                "metadata": {"duration_ms": 3200, "page": 6, "limit": 100, "returned": 0},
            }
        )

    previous_warning = settings.users_admin_alert_error_rate_warning_pct
    previous_critical = settings.users_admin_alert_error_rate_critical_pct
    try:
        settings.users_admin_alert_error_rate_warning_pct = 1.0
        settings.users_admin_alert_error_rate_critical_pct = 2.0
        response = client.get("/api/v1/users/admin/dashboard", headers=headers)
    finally:
        settings.users_admin_alert_error_rate_warning_pct = previous_warning
        settings.users_admin_alert_error_rate_critical_pct = previous_critical

    assert response.status_code == 200, response.text
    payload = response.json()
    assert isinstance(payload.get("alerts"), list)
    assert any(item.get("code") == "users.admin.error_rate.critical" for item in payload["alerts"])
