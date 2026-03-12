from __future__ import annotations

import logging
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.observability import observability_state  # noqa: E402
from app.main import app  # noqa: E402
from tests.test_auth import (  # noqa: E402
    _create_section_payload,
    _seed_canonical_structure,
    _setup_fake_db,
)
from tests.test_main_missing_blocks import _admin_headers  # noqa: E402


def percentile(values: list[float], target: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * target)))
    return ordered[index]


def timed_run(label: str, iterations: int, func: Callable[[], None]) -> dict[str, float]:
    samples_ms: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        func()
        samples_ms.append((time.perf_counter() - started) * 1000)
    return {
        "label": label,
        "iterations": float(iterations),
        "avg_ms": statistics.mean(samples_ms),
        "p95_ms": percentile(samples_ms, 0.95),
        "max_ms": max(samples_ms),
    }


def assert_threshold(metric: dict[str, float], *, p95_ms: float, avg_ms: float) -> None:
    if metric["p95_ms"] > p95_ms:
        raise SystemExit(
            f"{metric['label']} p95 regression: {metric['p95_ms']:.2f} ms > threshold {p95_ms:.2f} ms"
        )
    if metric["avg_ms"] > avg_ms:
        raise SystemExit(
            f"{metric['label']} avg regression: {metric['avg_ms']:.2f} ms > threshold {avg_ms:.2f} ms"
        )


def main() -> int:
    fake_db = _setup_fake_db()
    observability_state.reset()
    logging.getLogger("caps_api").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    with TestClient(app) as client:
        headers = _admin_headers(client, "admin_perf_smoke@example.com")
        teacher_headers = _role_headers(client, "teacher_perf_smoke@example.com", role="teacher")
        student_headers = _role_headers(client, "student_perf_smoke@example.com", role="student")

        for index in range(40):
            fake_db.audit_logs.items.append(
                {
                    "_id": f"audit-{index}",
                    "action_type": "login" if index % 4 == 0 else "request",
                    "action": "error" if index % 11 == 0 else "ok",
                    "severity": "high" if index % 13 == 0 else "low",
                    "actor_user_id": f"user-{index % 5}",
                    "entity_type": "api",
                    "detail": f"perf-seed-{index}",
                    "created_at": datetime.now(timezone.utc),
                }
            )

        client.get("/health")
        client.get("/api/v1/admin/system/health", headers=headers)
        assignment = client.post(
            "/api/v1/assignments/",
            json={"title": "Perf Smoke Assignment", "description": "Perf smoke", "total_marks": 100},
            headers=teacher_headers,
        )
        _assert_ok(assignment, expected_status=201)
        assignment_id = assignment.json()["id"]
        submission = client.post(
            "/api/v1/submissions/upload",
            data={"assignment_id": assignment_id, "notes": "perf smoke"},
            files={"file": ("perf.txt", b"performance smoke submission", "text/plain")},
            headers=student_headers,
        )
        _assert_ok(submission, expected_status=201)
        submission_id = submission.json()["id"]
        evaluation = client.post(
            "/api/v1/evaluations/",
            json={
                "submission_id": submission_id,
                "attendance_percent": 92,
                "skill": 2.0,
                "behavior": 2.0,
                "report": 8,
                "viva": 16,
                "final_exam": 50,
                "is_finalized": False,
            },
            headers=teacher_headers,
        )
        _assert_ok(evaluation, expected_status=201)
        evaluation_id = evaluation.json()["id"]
        structure = _seed_canonical_structure(fake_db, suffix="PERF", semester_number=3)
        section_ids: list[str] = []
        for index in range(12):
            section = client.post(
                "/api/v1/sections/",
                json=_create_section_payload(structure, name=f"Perf Section {index:02d}"),
                headers=headers,
            )
            _assert_ok(section, expected_status=201)
            section_ids.append(section.json()["id"])

        health_metric = timed_run(
            "health_check",
            25,
            lambda: _assert_ok(client.get("/health")),
        )
        system_health_metric = timed_run(
            "admin_system_health",
            20,
            lambda: _assert_ok(client.get("/api/v1/admin/system/health", headers=headers)),
        )
        login_metric = timed_run(
            "auth_login",
            15,
            lambda: _assert_ok(
                client.post(
                    "/api/v1/auth/login",
                    json={"email": "admin_perf_smoke@example.com", "password": "password123"},
                )
            ),
        )
        teacher_submission_list_metric = timed_run(
            "teacher_submission_list",
            15,
            lambda: _assert_submission_list(
                client.get(f"/api/v1/submissions/?assignment_id={assignment_id}", headers=teacher_headers),
                expected_submission_id=submission_id,
            ),
        )
        admin_section_list_metric = timed_run(
            "admin_section_list",
            15,
            lambda: _assert_section_list(
                client.get("/api/v1/sections/?skip=0&limit=50", headers=headers),
                expected_section_id=section_ids[0],
                expected_min_count=len(section_ids),
            ),
        )
        student_create_counter = [0]
        admin_student_create_metric = timed_run(
            "admin_student_create",
            12,
            lambda: _assert_student_create(
                client.post(
                    "/api/v1/students/",
                    json={
                        "full_name": f"Perf Student {student_create_counter[0]:02d}",
                        "roll_number": f"PERF-STU-{student_create_counter[0]:04d}",
                        "class_id": section_ids[0],
                    },
                    headers=headers,
                ),
                expected_roll_number=f"PERF-STU-{student_create_counter[0]:04d}",
                next_counter=student_create_counter,
            ),
        )
        teacher_review_workflow_metric = timed_run(
            "teacher_review_workflow",
            12,
            lambda: _assert_teacher_review_workflow(
                client=client,
                teacher_headers=teacher_headers,
                assignment_id=assignment_id,
                submission_id=submission_id,
                evaluation_id=evaluation_id,
            ),
        )

    metrics = [
        health_metric,
        system_health_metric,
        login_metric,
        teacher_submission_list_metric,
        admin_section_list_metric,
        admin_student_create_metric,
        teacher_review_workflow_metric,
    ]
    for metric in metrics:
        print(
            f"{metric['label']}: avg={metric['avg_ms']:.2f}ms "
            f"p95={metric['p95_ms']:.2f}ms max={metric['max_ms']:.2f}ms"
        )

    assert_threshold(
        health_metric,
        p95_ms=float(os.getenv("PERF_SMOKE_HEALTH_P95_MS", "120")),
        avg_ms=float(os.getenv("PERF_SMOKE_HEALTH_AVG_MS", "40")),
    )
    assert_threshold(
        system_health_metric,
        p95_ms=float(os.getenv("PERF_SMOKE_SYSTEM_HEALTH_P95_MS", "350")),
        avg_ms=float(os.getenv("PERF_SMOKE_SYSTEM_HEALTH_AVG_MS", "180")),
    )
    assert_threshold(
        login_metric,
        p95_ms=float(os.getenv("PERF_SMOKE_LOGIN_P95_MS", "380")),
        avg_ms=float(os.getenv("PERF_SMOKE_LOGIN_AVG_MS", "280")),
    )
    assert_threshold(
        teacher_submission_list_metric,
        p95_ms=float(os.getenv("PERF_SMOKE_TEACHER_SUBMISSION_LIST_P95_MS", "220")),
        avg_ms=float(os.getenv("PERF_SMOKE_TEACHER_SUBMISSION_LIST_AVG_MS", "120")),
    )
    assert_threshold(
        admin_section_list_metric,
        p95_ms=float(os.getenv("PERF_SMOKE_ADMIN_SECTION_LIST_P95_MS", "260")),
        avg_ms=float(os.getenv("PERF_SMOKE_ADMIN_SECTION_LIST_AVG_MS", "150")),
    )
    assert_threshold(
        admin_student_create_metric,
        p95_ms=float(os.getenv("PERF_SMOKE_ADMIN_STUDENT_CREATE_P95_MS", "320")),
        avg_ms=float(os.getenv("PERF_SMOKE_ADMIN_STUDENT_CREATE_AVG_MS", "180")),
    )
    assert_threshold(
        teacher_review_workflow_metric,
        p95_ms=float(os.getenv("PERF_SMOKE_TEACHER_REVIEW_WORKFLOW_P95_MS", "800")),
        avg_ms=float(os.getenv("PERF_SMOKE_TEACHER_REVIEW_WORKFLOW_AVG_MS", "450")),
    )

    print("Performance smoke checks passed.")
    return 0


def _assert_ok(response, *, expected_status: int = 200) -> None:
    assert response.status_code == expected_status, response.text


def _assert_submission_list(response, *, expected_submission_id: str) -> None:
    _assert_ok(response)
    payload = response.json()
    assert isinstance(payload, list)
    assert any(item.get("id") == expected_submission_id for item in payload)


def _assert_section_list(response, *, expected_section_id: str, expected_min_count: int) -> None:
    _assert_ok(response)
    payload = response.json()
    assert isinstance(payload, list)
    assert len(payload) >= expected_min_count
    assert any(item.get("id") == expected_section_id for item in payload)


def _assert_student_create(response, *, expected_roll_number: str, next_counter: list[int]) -> None:
    _assert_ok(response, expected_status=201)
    payload = response.json()
    assert payload.get("roll_number") == expected_roll_number
    next_counter[0] += 1


def _assert_teacher_review_workflow(
    *,
    client: TestClient,
    teacher_headers: dict[str, str],
    assignment_id: str,
    submission_id: str,
    evaluation_id: str,
) -> None:
    _assert_submission_list(
        client.get(f"/api/v1/submissions/?assignment_id={assignment_id}", headers=teacher_headers),
        expected_submission_id=submission_id,
    )
    _assert_evaluation_list(
        client.get(f"/api/v1/evaluations/?submission_id={submission_id}", headers=teacher_headers),
        expected_evaluation_id=evaluation_id,
    )
    _assert_analytics_summary(
        client.get("/api/v1/analytics/summary", headers=teacher_headers),
        expected_role="teacher",
    )


def _assert_evaluation_list(response, *, expected_evaluation_id: str) -> None:
    _assert_ok(response)
    payload = response.json()
    assert isinstance(payload, list)
    assert any(item.get("id") == expected_evaluation_id for item in payload)


def _assert_analytics_summary(response, *, expected_role: str) -> None:
    _assert_ok(response)
    payload = response.json()
    assert payload.get("role") == expected_role
    assert isinstance(payload.get("summary"), dict)


def _role_headers(client: TestClient, email: str, *, role: str) -> dict[str, str]:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": f"{role.title()} Perf User",
            "email": email,
            "password": "password123",
            "role": role,
        },
    )
    _assert_ok(register, expected_status=201)
    login = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "password123"},
    )
    _assert_ok(login)
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


if __name__ == "__main__":
    raise SystemExit(main())
