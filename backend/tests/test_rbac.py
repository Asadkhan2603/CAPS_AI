import asyncio

from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints import admin_rbac as admin_rbac_endpoint
from app.services import rbac as rbac_service
from tests.test_auth import (
    FakeUsersCollection,
    _create_section_payload,
    _register_and_login,
    _seed_canonical_structure,
    _setup_fake_db,
)


def _setup_fake_rbac_db():
    fake_db = _setup_fake_db()
    for collection_name in ("roles", "permissions", "role_permissions", "user_permissions", "scopes"):
        setattr(fake_db, collection_name, FakeUsersCollection())
    admin_rbac_endpoint.db = fake_db
    rbac_service.core_db = fake_db
    return fake_db


def test_super_admin_login_exposes_seeded_rbac_permissions() -> None:
    _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.rbac@example.com",
        role="admin",
    )

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    payload = me.json()
    assert payload["rbac_role_code"] == "SUPER_ADMIN"
    assert payload["admin_role"]["code"] == "SUPER_ADMIN"
    assert "student_management.assign_role" in payload["permissions"]
    assert "reports.generate" in payload["permissions"]


def test_super_admin_can_create_scoped_admin_with_permission_overrides() -> None:
    _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.manage@example.com",
        role="admin",
    )

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Department HOD",
            "email": "hod.rbac@example.com",
            "password": "password123",
            "role_code": "HOD",
            "allow_permission_keys": ["reports.approve"],
            "deny_permission_keys": ["complaints.view"],
            "scopes": [{"department_id": "dep-cse"}],
            "is_active": True,
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text
    created_payload = created.json()
    assert created_payload["admin_role"]["code"] == "HOD"
    assert created_payload["scopes"][0]["department_id"] == "dep-cse"
    assert "reports.approve" in created_payload["permissions"]
    assert "complaints.view" not in created_payload["permissions"]

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.rbac@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert me.status_code == 200, me.text
    me_payload = me.json()
    assert me_payload["rbac_role_code"] == "HOD"
    assert "reports.approve" in me_payload["permissions"]
    assert "complaints.view" not in me_payload["permissions"]


def test_non_super_admin_cannot_access_rbac_management_endpoints() -> None:
    _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.forbidden@example.com",
        role="admin",
    )
    create_hod = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.forbidden@example.com",
            "password": "password123",
            "role_code": "HOD",
            "scopes": [{"department_id": "dep-it"}],
        },
        headers=super_headers,
    )
    assert create_hod.status_code == 201, create_hod.text

    hod_login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.forbidden@example.com", "password": "password123"},
    )
    hod_headers = {"Authorization": f"Bearer {hod_login.json()['access_token']}"}
    forbidden = client.get("/api/v1/admin/rbac/roles", headers=hod_headers)
    assert forbidden.status_code == 403


def test_super_admin_can_create_update_and_delete_custom_role() -> None:
    _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.roles@example.com",
        role="admin",
    )

    created = client.post(
        "/api/v1/admin/rbac/roles",
        json={
            "code": "REPORT_REVIEWER",
            "name": "Report Reviewer",
            "description": "Custom reporting role",
            "permission_keys": ["reports.view", "reports.approve"],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text
    role_id = created.json()["id"]
    assert created.json()["code"] == "REPORT_REVIEWER"

    updated = client.patch(
        f"/api/v1/admin/rbac/roles/{role_id}",
        json={
            "permission_keys": ["reports.view", "reports.generate"],
        },
        headers=super_headers,
    )
    assert updated.status_code == 200, updated.text
    assert "reports.generate" in updated.json()["permission_keys"]

    deleted = client.delete(f"/api/v1/admin/rbac/roles/{role_id}", headers=super_headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["is_active"] is False


def test_scope_filter_builds_or_query_for_multiple_assignments() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.scope@example.com",
        role="admin",
    )
    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped Dean",
            "email": "dean.scope@example.com",
            "password": "password123",
            "role_code": "DEAN",
            "scopes": [{"department_id": "dep-a"}, {"year_id": "2027"}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text
    user = next(item for item in fake_db.users.items if item.get("email") == "dean.scope@example.com")

    scope_filter = asyncio.run(
        rbac_service.build_user_scope_filter(
            user,
            department_field="department_id",
            year_field="year_id",
            database=fake_db,
        )
    )
    assert scope_filter == {"$or": [{"department_id": "dep-a"}, {"year_id": "2027"}]}


def test_scoped_admin_only_lists_sections_students_and_enrollments_within_scope() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.scope-lists@example.com",
        role="admin",
    )

    structure_a = _seed_canonical_structure(fake_db, suffix="A")
    structure_b = _seed_canonical_structure(fake_db, suffix="B")
    section_a = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure_a, name="Section A"),
        headers=super_headers,
    )
    section_b = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure_b, name="Section B"),
        headers=super_headers,
    )
    assert section_a.status_code == 201, section_a.text
    assert section_b.status_code == 201, section_b.text

    student_a = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Alice Scope",
            "roll_number": "ROLL-A",
            "email": "alice.scope@example.com",
            "class_id": section_a.json()["id"],
        },
        headers=super_headers,
    )
    student_b = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Bob Scope",
            "roll_number": "ROLL-B",
            "email": "bob.scope@example.com",
            "class_id": section_b.json()["id"],
        },
        headers=super_headers,
    )
    assert student_a.status_code == 201, student_a.text
    assert student_b.status_code == 201, student_b.text

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.scope-lists@example.com",
            "password": "password123",
            "role_code": "HOD",
            "allow_permission_keys": ["student_management.view", "student_management.edit"],
            "scopes": [{"department_id": structure_a["department_id"]}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    hod_login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.scope-lists@example.com", "password": "password123"},
    )
    hod_headers = {"Authorization": f"Bearer {hod_login.json()['access_token']}"}

    sections_response = client.get("/api/v1/sections/", headers=hod_headers)
    students_response = client.get("/api/v1/students/", headers=hod_headers)
    enrollments_response = client.get("/api/v1/enrollments/", headers=hod_headers)

    assert sections_response.status_code == 200, sections_response.text
    assert students_response.status_code == 200, students_response.text
    assert enrollments_response.status_code == 200, enrollments_response.text
    assert [item["name"] for item in sections_response.json()] == ["Section A"]
    assert [item["roll_number"] for item in students_response.json()] == ["ROLL-A"]
    assert [item["class_id"] for item in enrollments_response.json()] == [section_a.json()["id"]]


def test_scoped_admin_cannot_access_out_of_scope_sections_and_students() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.scope-get@example.com",
        role="admin",
    )

    structure_a = _seed_canonical_structure(fake_db, suffix="GA")
    structure_b = _seed_canonical_structure(fake_db, suffix="GB")
    section_b = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure_b, name="Section B"),
        headers=super_headers,
    )
    assert section_b.status_code == 201, section_b.text
    student_b = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Bob Out",
            "roll_number": "ROLL-OUT",
            "email": "bob.out@example.com",
            "class_id": section_b.json()["id"],
        },
        headers=super_headers,
    )
    assert student_b.status_code == 201, student_b.text

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.scope-get@example.com",
            "password": "password123",
            "role_code": "HOD",
            "allow_permission_keys": ["student_management.view"],
            "scopes": [{"department_id": structure_a["department_id"]}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    hod_login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.scope-get@example.com", "password": "password123"},
    )
    hod_headers = {"Authorization": f"Bearer {hod_login.json()['access_token']}"}

    denied_section = client.get(f"/api/v1/sections/{section_b.json()['id']}", headers=hod_headers)
    denied_student = client.get(f"/api/v1/students/{student_b.json()['id']}", headers=hod_headers)

    assert denied_section.status_code == 403
    assert denied_student.status_code == 403


def test_scoped_admin_cannot_create_students_or_enrollments_outside_scope() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.scope-write@example.com",
        role="admin",
    )

    structure_a = _seed_canonical_structure(fake_db, suffix="WA")
    structure_b = _seed_canonical_structure(fake_db, suffix="WB")
    section_a = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure_a, name="Section A"),
        headers=super_headers,
    )
    section_b = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure_b, name="Section B"),
        headers=super_headers,
    )
    assert section_a.status_code == 201, section_a.text
    assert section_b.status_code == 201, section_b.text

    student_a = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Alice Write",
            "roll_number": "ROLL-WRITE",
            "email": "alice.write@example.com",
            "class_id": section_a.json()["id"],
        },
        headers=super_headers,
    )
    assert student_a.status_code == 201, student_a.text

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.scope-write@example.com",
            "password": "password123",
            "role_code": "HOD",
            "allow_permission_keys": [
                "student_management.view",
                "student_management.create",
                "student_management.edit",
            ],
            "scopes": [{"department_id": structure_a["department_id"]}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    hod_login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.scope-write@example.com", "password": "password123"},
    )
    hod_headers = {"Authorization": f"Bearer {hod_login.json()['access_token']}"}

    denied_student_create = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Blocked Student",
            "roll_number": "ROLL-BLOCK",
            "email": "blocked.student@example.com",
            "class_id": section_b.json()["id"],
        },
        headers=hod_headers,
    )
    denied_enrollment = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section_b.json()["id"], "student_id": student_a.json()["id"]},
        headers=hod_headers,
    )

    assert denied_student_create.status_code == 403
    assert denied_enrollment.status_code == 403


def test_scoped_admin_program_access_is_limited_to_assigned_department() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.program-scope@example.com",
        role="admin",
    )

    structure_a = _seed_canonical_structure(fake_db, suffix="PA")
    structure_b = _seed_canonical_structure(fake_db, suffix="PB")
    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.program-scope@example.com",
            "password": "password123",
            "role_code": "HOD",
            "allow_permission_keys": [
                "student_management.create",
                "student_management.edit",
                "student_management.delete",
            ],
            "scopes": [{"department_id": structure_a["department_id"]}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    hod_login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.program-scope@example.com", "password": "password123"},
    )
    hod_headers = {"Authorization": f"Bearer {hod_login.json()['access_token']}"}

    listed = client.get("/api/v1/programs/", headers=hod_headers)
    denied_get = client.get(f"/api/v1/programs/{structure_b['program_id']}", headers=hod_headers)
    denied_create = client.post(
        "/api/v1/programs/",
        json={
            "name": "Blocked Program",
            "code": "PRGBLOCK",
            "department_id": structure_b["department_id"],
            "duration_years": 4,
        },
        headers=hod_headers,
    )

    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [structure_a["program_id"]]
    assert denied_get.status_code == 403
    assert denied_create.status_code == 403


def test_scoped_admin_cannot_manage_departments_faculties_or_global_analytics() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.global-guard@example.com",
        role="admin",
    )

    structure_a = _seed_canonical_structure(fake_db, suffix="FA")
    structure_b = _seed_canonical_structure(fake_db, suffix="FB")
    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.global-guard@example.com",
            "password": "password123",
            "role_code": "HOD",
            "allow_permission_keys": [
                "faculty_management.create",
                "faculty_management.edit",
                "faculty_management.delete",
                "student_management.create",
                "student_management.edit",
                "student_management.delete",
                "reports.view",
            ],
            "scopes": [{"department_id": structure_a["department_id"]}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    hod_login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.global-guard@example.com", "password": "password123"},
    )
    hod_headers = {"Authorization": f"Bearer {hod_login.json()['access_token']}"}

    faculties_list = client.get("/api/v1/faculties/", headers=hod_headers)
    denied_department_write = client.put(
        f"/api/v1/departments/{structure_a['department_id']}",
        json={"name": "Blocked Department Rename"},
        headers=hod_headers,
    )
    denied_faculty_write = client.put(
        f"/api/v1/faculties/{structure_b['faculty_id']}",
        json={"name": "Blocked Faculty Rename"},
        headers=hod_headers,
    )
    denied_analytics = client.get("/api/v1/admin/analytics/overview", headers=hod_headers)

    assert faculties_list.status_code == 200, faculties_list.text
    assert [item["id"] for item in faculties_list.json()] == [structure_a["faculty_id"]]
    assert denied_department_write.status_code == 403
    assert denied_faculty_write.status_code == 403
    assert denied_analytics.status_code == 403


def test_permission_deny_overrides_block_legacy_admin_routes() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.override@example.com",
        role="admin",
    )

    structure = _seed_canonical_structure(fake_db, suffix="OVR")
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Override Section"),
        headers=super_headers,
    )
    assert section.status_code == 201, section.text

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Academic Admin",
            "email": "academic.override@example.com",
            "password": "password123",
            "role_code": "ACADEMIC_ADMIN",
            "deny_permission_keys": [
                "student_management.create",
                "student_management.edit",
                "student_management.delete",
            ],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "academic.override@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    denied = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Denied Student",
            "roll_number": "ROLL-DENY",
            "email": "denied.student@example.com",
            "class_id": section.json()["id"],
        },
        headers=headers,
    )

    assert denied.status_code == 403


def test_rbac_mutations_write_audit_logs() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.audit@example.com",
        role="admin",
    )

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Audited Admin",
            "email": "audited.admin@example.com",
            "password": "password123",
            "role_code": "HOD",
            "scopes": [{"department_id": "dep-audit"}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    action_types = {item.get("action_type") for item in fake_db.audit_logs.items}
    assert "rbac_admin_create" in action_types


def test_year_admin_scope_matches_batch_start_year_cohort() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.year-scope@example.com",
        role="admin",
    )

    structure_a = _seed_canonical_structure(fake_db, suffix="YA", start_year=2027)
    structure_b = _seed_canonical_structure(fake_db, suffix="YB", start_year=2028)
    section_a = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure_a, name="Year 2027 Section"),
        headers=super_headers,
    )
    section_b = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure_b, name="Year 2028 Section"),
        headers=super_headers,
    )
    assert section_a.status_code == 201, section_a.text
    assert section_b.status_code == 201, section_b.text

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped Year Admin",
            "email": "year.admin.scope@example.com",
            "password": "password123",
            "role_code": "YEAR_ADMIN",
            "allow_permission_keys": ["student_management.view"],
            "scopes": [{"year_id": "2027"}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "year.admin.scope@example.com", "password": "password123"},
    )
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    sections_response = client.get("/api/v1/sections/", headers=headers)
    batches_response = client.get("/api/v1/batches/", headers=headers)

    assert sections_response.status_code == 200, sections_response.text
    assert [item["name"] for item in sections_response.json()] == ["Year 2027 Section"]
    assert batches_response.status_code == 200, batches_response.text
    assert [item["id"] for item in batches_response.json()] == [structure_a["batch_id"]]


def test_super_admin_cannot_deactivate_or_demote_self() -> None:
    _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.self-guard@example.com",
        role="admin",
    )
    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200, me.text
    admin_id = me.json()["id"]

    deactivate = client.patch(
        f"/api/v1/admin/rbac/admins/{admin_id}/status",
        json={"is_active": False},
        headers=headers,
    )
    demote = client.patch(
        f"/api/v1/admin/rbac/admins/{admin_id}",
        json={"role_code": "HOD"},
        headers=headers,
    )

    assert deactivate.status_code == 400
    assert demote.status_code == 400


def test_admin_update_audit_preserves_true_old_scope_and_override_values() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.audit-diff@example.com",
        role="admin",
    )

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.audit-diff@example.com",
            "password": "password123",
            "role_code": "HOD",
            "scopes": [{"department_id": "dep-a"}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text
    admin_id = created.json()["id"]

    updated = client.patch(
        f"/api/v1/admin/rbac/admins/{admin_id}",
        json={
            "scopes": [{"department_id": "dep-b"}],
            "allow_permission_keys": ["reports.approve"],
        },
        headers=super_headers,
    )
    assert updated.status_code == 200, updated.text

    audit_row = fake_db.audit_logs.items[-1]
    assert audit_row["action_type"] == "rbac_admin_update"
    assert audit_row["old_value"]["scopes"][0]["department_id"] == "dep-a"
    assert audit_row["new_value"]["scopes"][0]["department_id"] == "dep-b"
    assert audit_row["old_value"]["permission_overrides"] == {
        "allow_permission_keys": [],
        "deny_permission_keys": [],
    }
    assert audit_row["new_value"]["permission_overrides"] == {
        "allow_permission_keys": ["reports.approve"],
        "deny_permission_keys": [],
    }


def test_scoped_admin_batch_and_semester_access_is_limited_to_assigned_scope() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.batch-scope@example.com",
        role="admin",
    )

    structure_a = _seed_canonical_structure(fake_db, suffix="BA")
    structure_b = _seed_canonical_structure(fake_db, suffix="BB")
    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.batch-scope@example.com",
            "password": "password123",
            "role_code": "HOD",
            "allow_permission_keys": [
                "student_management.create",
                "student_management.edit",
                "student_management.delete",
            ],
            "scopes": [{"department_id": structure_a["department_id"]}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    hod_login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.batch-scope@example.com", "password": "password123"},
    )
    hod_headers = {"Authorization": f"Bearer {hod_login.json()['access_token']}"}

    batches_response = client.get("/api/v1/batches/", headers=hod_headers)
    semester_a = next(item for item in fake_db.semesters.items if item.get("batch_id") == structure_a["batch_id"])
    semester_b = next(item for item in fake_db.semesters.items if item.get("batch_id") == structure_b["batch_id"])
    denied_batch = client.get(f"/api/v1/batches/{structure_b['batch_id']}", headers=hod_headers)
    denied_semester = client.get(f"/api/v1/semesters/{str(semester_b['_id'])}", headers=hod_headers)
    denied_semester_create = client.post(
        "/api/v1/semesters/",
        json={"batch_id": structure_b["batch_id"], "semester_number": 2, "label": "Semester 2"},
        headers=hod_headers,
    )

    assert batches_response.status_code == 200, batches_response.text
    assert [item["id"] for item in batches_response.json()] == [structure_a["batch_id"]]
    semesters_response = client.get(f"/api/v1/semesters/?batch_id={structure_a['batch_id']}", headers=hod_headers)
    assert semesters_response.status_code == 200, semesters_response.text
    assert [item["id"] for item in semesters_response.json()] == [str(semester_a["_id"])]
    assert denied_batch.status_code == 403
    assert denied_semester.status_code == 403
    assert denied_semester_create.status_code == 403


def test_scoped_admin_specialization_access_is_limited_to_assigned_program_department() -> None:
    fake_db = _setup_fake_rbac_db()
    client = TestClient(app)

    _admin, super_headers = _register_and_login(
        client,
        full_name="Bootstrap Super Admin",
        email="superadmin.spec-scope@example.com",
        role="admin",
    )

    structure_a = _seed_canonical_structure(fake_db, suffix="SA")
    structure_b = _seed_canonical_structure(fake_db, suffix="SB")
    specialization_a = client.post(
        "/api/v1/specializations/",
        json={"name": "AI", "code": "AI", "program_id": structure_a["program_id"]},
        headers=super_headers,
    )
    specialization_b = client.post(
        "/api/v1/specializations/",
        json={"name": "Cyber", "code": "CYB", "program_id": structure_b["program_id"]},
        headers=super_headers,
    )
    assert specialization_a.status_code == 201, specialization_a.text
    assert specialization_b.status_code == 201, specialization_b.text

    created = client.post(
        "/api/v1/admin/rbac/admins",
        json={
            "full_name": "Scoped HOD",
            "email": "hod.spec-scope@example.com",
            "password": "password123",
            "role_code": "HOD",
            "allow_permission_keys": [
                "student_management.create",
                "student_management.edit",
                "student_management.delete",
            ],
            "scopes": [{"department_id": structure_a["department_id"]}],
        },
        headers=super_headers,
    )
    assert created.status_code == 201, created.text

    hod_login = client.post(
        "/api/v1/auth/login",
        json={"email": "hod.spec-scope@example.com", "password": "password123"},
    )
    hod_headers = {"Authorization": f"Bearer {hod_login.json()['access_token']}"}

    listed = client.get("/api/v1/specializations/", headers=hod_headers)
    denied_get = client.get(f"/api/v1/specializations/{specialization_b.json()['id']}", headers=hod_headers)
    denied_create = client.post(
        "/api/v1/specializations/",
        json={"name": "Blocked Spec", "code": "BLK", "program_id": structure_b["program_id"]},
        headers=hod_headers,
    )

    assert listed.status_code == 200, listed.text
    assert [item["id"] for item in listed.json()] == [specialization_a.json()["id"]]
    assert denied_get.status_code == 403
    assert denied_create.status_code == 403
