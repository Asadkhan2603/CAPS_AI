from datetime import datetime, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from tests.test_auth import (
    FakeUsersCollection,
    _create_section_payload,
    _register_and_login,
    _seed_canonical_structure,
    _setup_fake_db,
)


def _ensure_cr_collections(fake_db) -> None:
    if not hasattr(fake_db, "users_admin_telemetry"):
        fake_db.users_admin_telemetry = FakeUsersCollection()


def _user_doc(fake_db, user_id: str) -> dict:
    return next(item for item in fake_db.users.items if str(item.get("_id")) == user_id)


def _student_doc(fake_db, user_id: str) -> dict:
    return next(item for item in fake_db.students.items if str(item.get("user_id")) == user_id)


def _assign_student_to_section(fake_db, user: dict, section_id: str, *, roll_number: str) -> dict:
    student = _student_doc(fake_db, user["id"])
    student.update(
        {
            "user_id": user["id"],
            "email": user["email"],
            "full_name": user["full_name"],
            "class_id": section_id,
            "roll_number": roll_number,
            "is_active": True,
        }
    )
    return student


def _setup_cr_section() -> tuple:
    fake_db = _setup_fake_db()
    _ensure_cr_collections(fake_db)
    client = TestClient(app)

    admin, admin_headers = _register_and_login(
        client,
        full_name="CR Admin",
        email="cr.admin@example.com",
        role="admin",
    )
    year_head, year_head_headers = _register_and_login(
        client,
        full_name="Year Head CR",
        email="cr.yearhead@example.com",
        role="teacher",
        extended_roles=["year_head"],
    )
    coordinator, _coordinator_headers = _register_and_login(
        client,
        full_name="Coordinator CR",
        email="cr.coordinator@example.com",
        role="teacher",
    )

    structure = _seed_canonical_structure(fake_db, suffix="CR", semester_number=4)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="CSE CR Section",
            class_coordinator_user_id=coordinator["id"],
            faculty_name="Faculty CR",
        ),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text
    section_id = section.json()["id"]

    student_one, student_one_headers = _register_and_login(
        client,
        full_name="Student CR One",
        email="cr.student.one@example.com",
        role="student",
    )
    student_two, student_two_headers = _register_and_login(
        client,
        full_name="Student CR Two",
        email="cr.student.two@example.com",
        role="student",
    )
    student_other, student_other_headers = _register_and_login(
        client,
        full_name="Student Other Section",
        email="cr.student.other@example.com",
        role="student",
    )
    _assign_student_to_section(fake_db, student_one, section_id, roll_number="CR001")
    _assign_student_to_section(fake_db, student_two, section_id, roll_number="CR002")

    other_section_id = ObjectId()
    fake_db.classes.items.append(
        {
            "_id": other_section_id,
            "name": "Other CR Section",
            "faculty_id": structure["faculty_id"],
            "department_id": structure["department_id"],
            "program_id": structure["program_id"],
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "is_active": True,
        }
    )
    _assign_student_to_section(fake_db, student_other, str(other_section_id), roll_number="CR999")

    fake_db.users.items.append(
        {
            "_id": ObjectId(),
            "full_name": "HOD Contact",
            "email": "hod.contact@example.com",
            "hashed_password": "unused",
            "role": "admin",
            "admin_type": "hod",
            "extended_roles": [],
            "profile": {"phone": "1112223333"},
            "is_active": True,
        }
    )
    fake_db.users.items.append(
        {
            "_id": ObjectId(),
            "full_name": "Dean Contact",
            "email": "dean.contact@example.com",
            "hashed_password": "unused",
            "role": "admin",
            "admin_type": "dean",
            "extended_roles": [],
            "profile": {},
            "is_active": True,
        }
    )

    fake_db.assignments.items.append(
        {
            "_id": ObjectId(),
            "title": "CR Assignment",
            "class_id": section_id,
            "status": "open",
            "due_date": datetime(2026, 4, 20, tzinfo=timezone.utc),
            "created_at": datetime(2026, 4, 15, tzinfo=timezone.utc),
        }
    )

    return {
        "fake_db": fake_db,
        "client": client,
        "admin": admin,
        "admin_headers": admin_headers,
        "year_head": year_head,
        "year_head_headers": year_head_headers,
        "section_id": section_id,
        "student_one": student_one,
        "student_one_headers": student_one_headers,
        "student_two": student_two,
        "student_two_headers": student_two_headers,
        "student_other": student_other,
        "student_other_headers": student_other_headers,
    }


def test_cr_representative_assignment_replacement_and_remove() -> None:
    ctx = _setup_cr_section()
    client = ctx["client"]
    fake_db = ctx["fake_db"]
    section_id = ctx["section_id"]
    admin_headers = ctx["admin_headers"]

    listed = client.get(f"/api/v1/sections/{section_id}/representatives", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert len(listed.json()["candidate_students"]) >= 2

    assigned = client.put(
        f"/api/v1/sections/{section_id}/representatives/cr_1",
        json={"student_user_id": ctx["student_one"]["id"], "reason": "Elected by class"},
        headers=admin_headers,
    )
    assert assigned.status_code == 200, assigned.text
    assert assigned.json()["representatives"]["cr_1"]["user_id"] == ctx["student_one"]["id"]
    student_one_doc = _user_doc(fake_db, ctx["student_one"]["id"])
    assert "class_representative" in student_one_doc["extended_roles"]
    assert student_one_doc["role_scope"]["class_representative"]["seat"] == "cr_1"

    duplicate_seat = client.put(
        f"/api/v1/sections/{section_id}/representatives/cr_2",
        json={"student_user_id": ctx["student_one"]["id"], "reason": "Try duplicate seat"},
        headers=admin_headers,
    )
    assert duplicate_seat.status_code == 409, duplicate_seat.text

    replaced = client.put(
        f"/api/v1/sections/{section_id}/representatives/cr_1",
        json={"student_user_id": ctx["student_two"]["id"], "reason": "Replacement approved"},
        headers=admin_headers,
    )
    assert replaced.status_code == 200, replaced.text
    assert replaced.json()["representatives"]["cr_1"]["user_id"] == ctx["student_two"]["id"]
    assert "class_representative" not in _user_doc(fake_db, ctx["student_one"]["id"]).get("extended_roles", [])
    assert _user_doc(fake_db, ctx["student_two"]["id"])["role_scope"]["class_representative"]["seat"] == "cr_1"

    removed = client.request(
        "DELETE",
        f"/api/v1/sections/{section_id}/representatives/cr_1",
        json={"reason": "End of tenure"},
        headers=admin_headers,
    )
    assert removed.status_code == 200, removed.text
    assert removed.json()["representatives"]["cr_1"]["user_id"] is None
    assert "class_representative" not in _user_doc(fake_db, ctx["student_two"]["id"]).get("extended_roles", [])

    audit_actions = {item.get("action") for item in fake_db.audit_logs.items}
    assert "sections.assign_class_representative" in audit_actions
    assert "sections.remove_class_representative" in audit_actions
    telemetry_events = {item.get("event") for item in fake_db.users_admin_telemetry.items}
    assert "sections.class_representatives.assign" in telemetry_events
    assert "sections.class_representatives.replace" in telemetry_events
    assert "sections.class_representatives.remove" in telemetry_events


def test_cr_assignment_guardrails_for_inactive_non_student_and_cross_section() -> None:
    ctx = _setup_cr_section()
    client = ctx["client"]
    fake_db = ctx["fake_db"]
    section_id = ctx["section_id"]
    admin_headers = ctx["admin_headers"]

    _user_doc(fake_db, ctx["student_one"]["id"])["is_active"] = False
    inactive = client.put(
        f"/api/v1/sections/{section_id}/representatives/cr_1",
        json={"student_user_id": ctx["student_one"]["id"], "reason": "Inactive student"},
        headers=admin_headers,
    )
    assert inactive.status_code == 400, inactive.text
    assert inactive.json()["detail"] == "student_user_id must reference an active student user"
    _user_doc(fake_db, ctx["student_one"]["id"])["is_active"] = True

    non_student = client.put(
        f"/api/v1/sections/{section_id}/representatives/cr_1",
        json={"student_user_id": ctx["year_head"]["id"], "reason": "Teacher cannot be CR"},
        headers=admin_headers,
    )
    assert non_student.status_code == 400, non_student.text

    cross_section = client.put(
        f"/api/v1/sections/{section_id}/representatives/cr_1",
        json={"student_user_id": ctx["student_other"]["id"], "reason": "Wrong section"},
        headers=admin_headers,
    )
    assert cross_section.status_code == 400, cross_section.text
    assert cross_section.json()["detail"] == "Student is not assigned to the selected section"


def test_cr_dashboard_access_and_payload() -> None:
    ctx = _setup_cr_section()
    client = ctx["client"]
    fake_db = ctx["fake_db"]
    section_id = ctx["section_id"]

    assigned = client.put(
        f"/api/v1/sections/{section_id}/representatives/cr_2",
        json={"student_user_id": ctx["student_one"]["id"], "reason": "Dashboard access"},
        headers=ctx["admin_headers"],
    )
    assert assigned.status_code == 200, assigned.text

    dashboard = client.get(f"/api/v1/sections/{section_id}/representative-dashboard", headers=ctx["student_one_headers"])
    assert dashboard.status_code == 200, dashboard.text
    payload = dashboard.json()
    assert payload["section_id"] == section_id
    assert payload["seat"] == "cr_2"
    assert payload["generated_at"]
    assert payload["assignments"][0]["missing_submission_count"] == 2
    assert any(contact["label"] == "HOD" and contact["has_email"] is True for contact in payload["authority_contacts"])

    year_head_dashboard = client.get(f"/api/v1/sections/{section_id}/representative-dashboard", headers=ctx["year_head_headers"])
    assert year_head_dashboard.status_code == 200, year_head_dashboard.text

    denied = client.get(f"/api/v1/sections/{section_id}/representative-dashboard", headers=ctx["student_other_headers"])
    assert denied.status_code == 403, denied.text
    telemetry_events = {item.get("event") for item in fake_db.users_admin_telemetry.items}
    assert "sections.class_representatives.dashboard_load" in telemetry_events
    assert "sections.class_representatives.dashboard_access_denied" in telemetry_events
