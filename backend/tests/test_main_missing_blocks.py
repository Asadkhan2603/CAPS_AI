from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from tests.test_auth import _setup_fake_db


def _admin_headers(client: TestClient, email: str) -> dict:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": email,
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_evaluation_create_computes_totals_and_grade() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_eval@example.com")

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student User",
            "email": "student_eval@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Lab 1", "description": "Desc", "total_marks": 100},
        headers=headers,
    )
    assert assignment.status_code == 201

    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"], "notes": "submission"},
        files={"file": ("report.txt", b"machine learning report content", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 201

    created = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": upload.json()["id"],
            "attendance_percent": 95,
            "skill": 2.5,
            "behavior": 2.5,
            "report": 9,
            "viva": 18,
            "final_exam": 50,
            "remarks": "Good work",
            "is_finalized": False,
        },
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["internal_total"] == 37.0
    assert body["grand_total"] == 87.0
    assert body["grade"] == "A"
    assert len(fake_db.audit_logs.items) == 1


def test_similarity_run_creates_logs_and_updates_submission_score() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity@example.com")

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Lab 2", "description": "Desc", "total_marks": 100},
        headers=headers,
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]

    first = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("one.txt", b"deep learning and neural networks", "text/plain")},
        headers=headers,
    )
    second = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("two.txt", b"deep learning and neural networks basics", "text/plain")},
        headers=headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    run = client.post(f"/api/v1/similarity/checks/run/{first.json()['id']}", headers=headers)
    assert run.status_code == 200
    checks = run.json()
    assert len(checks) >= 1
    assert checks[0]["source_submission_id"] == first.json()["id"]
    assert fake_db.submissions.items[0]["similarity_score"] is not None


def test_notifications_create_list_and_mark_read() -> None:
    _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_notifications@example.com")

    created = client.post(
        "/api/v1/notifications/",
        json={"title": "Urgent", "message": "Freeze in 48h", "priority": "urgent", "scope": "global"},
        headers=headers,
    )
    assert created.status_code == 201
    notification_id = created.json()["id"]

    listed = client.get("/api/v1/notifications/", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    marked = client.patch(f"/api/v1/notifications/{notification_id}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True


def test_analytics_summary_returns_counts() -> None:
    _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_analytics@example.com")

    summary = client.get("/api/v1/analytics/summary", headers=headers)
    assert summary.status_code == 200
    body = summary.json()
    assert body["role"] == "admin"
    assert "summary" in body
    assert "users" in body["summary"]


def test_audit_logs_list_returns_entries() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_audit@example.com")

    fake_db.audit_logs.items.append(
        {
            "_id": ObjectId(),
            "actor_user_id": "u1",
            "action": "create",
            "entity_type": "evaluation",
            "entity_id": "e1",
            "detail": "Created evaluation",
        }
    )

    listed = client.get("/api/v1/audit-logs/?entity_type=evaluation", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) >= 1
