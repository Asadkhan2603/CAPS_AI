from fastapi.testclient import TestClient

from app.main import app
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


def test_scope_guardrail_class_coordinator_requires_section() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    teacher, _teacher_headers = _register_and_login(
        client,
        full_name="Teacher Guardrail",
        email="teacher.guardrail.class@example.com",
        role="teacher",
    )
    _admin, admin_headers = _register_and_login(
        client,
        full_name="Admin Guardrail",
        email="admin.guardrail.class@example.com",
        role="admin",
    )

    response = client.patch(
        f"/api/v1/users/{teacher['id']}/extensions",
        json={
            "extended_roles": ["class_coordinator"],
            "role_scope": {"class_coordinator": {}},
            "change_reason": "Assign class coordinator",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "class_coordinator requires class_coordinator.class_id"


def test_scope_guardrail_club_president_requires_club() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    student, _student_headers = _register_and_login(
        client,
        full_name="Student Guardrail",
        email="student.guardrail.club@example.com",
        role="student",
    )
    _admin, admin_headers = _register_and_login(
        client,
        full_name="Admin Guardrail",
        email="admin.guardrail.club@example.com",
        role="admin",
    )

    response = client.patch(
        f"/api/v1/users/{student['id']}/extensions",
        json={
            "extended_roles": ["club_president"],
            "role_scope": {"club_president": {}},
            "change_reason": "Assign club president",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "club_president requires club_president.club_id"


def test_scope_guardrail_class_representative_requires_section_and_seat() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    student, _student_headers = _register_and_login(
        client,
        full_name="Student CR Guardrail",
        email="student.guardrail.cr@example.com",
        role="student",
    )
    _admin, admin_headers = _register_and_login(
        client,
        full_name="Admin CR Guardrail",
        email="admin.guardrail.cr@example.com",
        role="admin",
    )

    missing_section = client.patch(
        f"/api/v1/users/{student['id']}/extensions",
        json={
            "extended_roles": ["class_representative"],
            "role_scope": {"class_representative": {"seat": "cr_1"}},
            "change_reason": "Assign CR without section",
        },
        headers=admin_headers,
    )
    assert missing_section.status_code == 400, missing_section.text
    assert missing_section.json()["detail"] == "class_representative requires class_representative.class_id"

    missing_seat = client.patch(
        f"/api/v1/users/{student['id']}/extensions",
        json={
            "extended_roles": ["class_representative"],
            "role_scope": {"class_representative": {"class_id": "section-1"}},
            "change_reason": "Assign CR without seat",
        },
        headers=admin_headers,
    )
    assert missing_seat.status_code == 400, missing_seat.text
    assert missing_seat.json()["detail"] == "class_representative requires class_representative.seat as cr_1 or cr_2"


def test_bulk_status_partial_failure_self_deactivation_blocked() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    target, _target_headers = _register_and_login(
        client,
        full_name="Teacher Target",
        email="teacher.bulk-status@example.com",
        role="teacher",
    )
    admin, admin_headers = _register_and_login(
        client,
        full_name="Admin Bulk",
        email="admin.bulk-status@example.com",
        role="admin",
    )

    response = client.post(
        "/api/v1/users/bulk/status",
        json={
            "user_ids": [admin["id"], target["id"]],
            "is_active": False,
            "reason": "Bulk lifecycle cleanup",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["updated_count"] == 1
    assert payload["failed_count"] == 1
    results = {row["user_id"]: row for row in payload["results"]}
    assert results[target["id"]]["success"] is True
    assert results[admin["id"]]["success"] is False
    assert "Cannot deactivate yourself" in (results[admin["id"]]["message"] or "")


def test_bulk_extensions_partial_failure_with_invalid_scope() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    invalid_teacher, _invalid_headers = _register_and_login(
        client,
        full_name="Teacher Invalid Scope",
        email="teacher.invalid-scope@example.com",
        role="teacher",
    )
    valid_teacher, _valid_headers = _register_and_login(
        client,
        full_name="Teacher Valid Scope",
        email="teacher.valid-scope@example.com",
        role="teacher",
    )
    _admin, admin_headers = _register_and_login(
        client,
        full_name="Admin Bulk Extensions",
        email="admin.bulk-extensions@example.com",
        role="admin",
    )

    response = client.patch(
        "/api/v1/users/bulk/extensions",
        json={
            "updates": [
                {
                    "user_id": invalid_teacher["id"],
                    "extended_roles": ["class_coordinator"],
                    "role_scope": {"class_coordinator": {}},
                },
                {
                    "user_id": valid_teacher["id"],
                    "extended_roles": ["year_head"],
                    "role_scope": {},
                },
            ],
            "change_reason": "Bulk role update",
        },
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["updated_count"] == 1
    assert payload["failed_count"] == 1
    results = {row["user_id"]: row for row in payload["results"]}
    assert results[valid_teacher["id"]]["success"] is True
    assert results[invalid_teacher["id"]]["success"] is False
    assert "class_coordinator requires class_coordinator.class_id" in (results[invalid_teacher["id"]]["message"] or "")
