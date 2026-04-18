from __future__ import annotations

from datetime import datetime, timezone
from types import MethodType

from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from tests.test_auth import FakeCursor, FakeUsersCollection, _register_and_login, _setup_fake_db


def _ensure_users_admin_collections(fake_db) -> None:
    if not hasattr(fake_db, "users_admin_telemetry"):
        fake_db.users_admin_telemetry = FakeUsersCollection()
    if not hasattr(fake_db, "user_filter_presets"):
        fake_db.user_filter_presets = FakeUsersCollection()
    if not hasattr(fake_db, "user_invitations"):
        fake_db.user_invitations = FakeUsersCollection()
    if not hasattr(fake_db, "user_permission_templates"):
        fake_db.user_permission_templates = FakeUsersCollection()


def _read_field(document: dict, field: str):
    value = document
    for part in field.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def _matches_pipeline_query(document: dict, query: dict) -> bool:
    for key, expected in (query or {}).items():
        value = _read_field(document, key)
        if isinstance(expected, dict):
            if "$in" in expected and value not in expected["$in"]:
                return False
            if "$nin" in expected and value in expected["$nin"]:
                return False
            if "$regex" in expected:
                candidate = str(value or "").lower()
                needle = str(expected["$regex"]).lower().replace("^", "").replace("$", "")
                if needle not in candidate:
                    return False
                continue
            if "$gte" in expected and (value is None or value < expected["$gte"]):
                return False
            if "$lte" in expected and (value is None or value > expected["$lte"]):
                return False
            continue
        if value != expected:
            return False
    return True


def _install_users_aggregate(fake_db) -> None:
    def aggregate(self, pipeline):
        rows = [dict(item) for item in self.items]
        for stage in pipeline:
            if "$match" in stage:
                rows = [row for row in rows if _matches_pipeline_query(row, stage["$match"])]
            elif "$unwind" in stage and stage["$unwind"] == "$extended_roles":
                expanded = []
                for row in rows:
                    roles = row.get("extended_roles") or []
                    for role in roles:
                        clone = dict(row)
                        clone["extended_roles"] = role
                        expanded.append(clone)
                rows = expanded
            elif "$group" in stage:
                group_key = str(stage["$group"]["_id"]).lstrip("$")
                grouped: dict[str | bool | None, int] = {}
                for row in rows:
                    key_value = _read_field(row, group_key)
                    grouped[key_value] = grouped.get(key_value, 0) + 1
                rows = [{"_id": key, "count": count} for key, count in grouped.items()]
            elif "$sort" in stage:
                sort_spec = stage["$sort"]
                for sort_key, direction in reversed(list(sort_spec.items())):
                    rows.sort(key=lambda item: item.get(sort_key), reverse=(direction == -1))
        return FakeCursor(rows)

    fake_db.users.aggregate = MethodType(aggregate, fake_db.users)


def _seed_admin_list_rows(fake_db) -> None:
    fake_db.users.items.extend(
        [
            {
                "_id": ObjectId(),
                "full_name": "Alpha Teacher",
                "email": "alpha.teacher@example.com",
                "hashed_password": "hashed",
                "role": "teacher",
                "admin_type": None,
                "is_active": True,
                "extended_roles": ["year_head"],
                "profile": {"department": "Engineering", "designation": "Lecturer"},
                "updated_at": datetime(2026, 4, 10, tzinfo=timezone.utc),
                "created_at": datetime(2026, 4, 10, tzinfo=timezone.utc),
            },
            {
                "_id": ObjectId(),
                "full_name": "Beta Teacher",
                "email": "beta.teacher@example.com",
                "hashed_password": "hashed",
                "role": "teacher",
                "admin_type": None,
                "is_active": False,
                "extended_roles": ["class_coordinator"],
                "profile": {"department": "Engineering", "designation": "Coordinator"},
                "updated_at": datetime(2026, 4, 11, tzinfo=timezone.utc),
                "created_at": datetime(2026, 4, 11, tzinfo=timezone.utc),
            },
            {
                "_id": ObjectId(),
                "full_name": "Gamma Admin",
                "email": "gamma.admin@example.com",
                "hashed_password": "hashed",
                "role": "admin",
                "admin_type": "super_admin",
                "is_active": True,
                "extended_roles": [],
                "profile": {"department": "Operations", "designation": "Platform Admin"},
                "updated_at": datetime(2026, 4, 12, tzinfo=timezone.utc),
                "created_at": datetime(2026, 4, 12, tzinfo=timezone.utc),
            },
        ]
    )


def test_users_admin_capabilities_contract() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Users Admin",
        email="users-admin-contract@example.com",
        role="admin",
    )

    response = client.get("/api/v1/users/admin/capabilities", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workspace"] is True
    assert payload["activity"] is True
    assert payload["bulk_operations"] is True
    assert payload["rollout_stage"] in {"internal_admins", "super_admins", "all_admins"}
    assert "rollout_cohort" in payload
    assert "rollout_access" in payload
    assert "rollout_reason" in payload


def test_users_admin_list_contract_with_pagination_and_filters() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Users Admin",
        email="users-admin-list@example.com",
        role="admin",
    )
    _seed_admin_list_rows(fake_db)

    response = client.get(
        "/api/v1/users/admin/list",
        params={"roles": "teacher", "is_active": "true", "page": 1, "limit": 25, "sort_by": "updated_at", "sort_dir": "desc"},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["page"] == 1
    assert payload["limit"] == 25
    assert payload["total"] >= 1
    assert payload["total_pages"] >= 1
    assert len(payload["items"]) >= 1
    first = payload["items"][0]
    assert set(
        [
            "id",
            "full_name",
            "email",
            "avatar_url",
            "avatar_updated_at",
            "role",
            "admin_type",
            "is_active",
            "extended_roles",
            "last_active_at",
            "created_at",
            "updated_at",
            "department",
            "designation",
        ]
    ).issubset(first.keys())
    assert first["role"] == "teacher"
    assert first["is_active"] is True


def test_users_filter_options_contract() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    _install_users_aggregate(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Users Admin",
        email="users-filter-options@example.com",
        role="admin",
    )
    _seed_admin_list_rows(fake_db)

    response = client.get("/api/v1/users/filter-options", headers=headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert set(payload.keys()) == {"roles", "admin_types", "extensions", "departments", "status"}
    assert any(item["value"] == "teacher" for item in payload["roles"])
    assert any(item["value"] == "super_admin" for item in payload["admin_types"])
    assert any(item["value"] == "year_head" for item in payload["extensions"])
    assert any(item["value"] == "Engineering" for item in payload["departments"])


def test_users_activity_endpoint_contract_with_pagination() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    user, user_headers = _register_and_login(
        client,
        full_name="Teacher Activity",
        email="teacher.activity@example.com",
        role="teacher",
    )
    _admin, admin_headers = _register_and_login(
        client,
        full_name="Admin Activity",
        email="admin.activity@example.com",
        role="admin",
    )
    fake_db.audit_logs.items.extend(
        [
            {
                "_id": ObjectId(),
                "entity_type": "user",
                "entity_id": user["id"],
                "action": "update_extensions",
                "severity": "medium",
                "detail": "Updated extensions",
                "created_at": datetime(2026, 4, 13, tzinfo=timezone.utc),
            },
            {
                "_id": ObjectId(),
                "actor_user_id": user["id"],
                "action": "login",
                "severity": "low",
                "detail": "User login",
                "created_at": datetime(2026, 4, 14, tzinfo=timezone.utc),
            },
        ]
    )

    # Keep user session active to ensure route works for both actor and admin requestors.
    assert user_headers["Authorization"].startswith("Bearer ")
    response = client.get(f"/api/v1/users/{user['id']}/activity", params={"page": 1, "limit": 10}, headers=admin_headers)
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["page"] == 1
    assert payload["limit"] == 10
    assert payload["total"] >= 2
    assert payload["total_pages"] >= 1
    assert len(payload["items"]) >= 2
    assert all("id" in item for item in payload["items"])


def test_users_status_patch_requires_reason() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    target, _target_headers = _register_and_login(
        client,
        full_name="Teacher Target",
        email="teacher.status-target@example.com",
        role="teacher",
    )
    _admin, admin_headers = _register_and_login(
        client,
        full_name="Admin Status",
        email="admin.status@example.com",
        role="admin",
    )

    response = client.patch(
        f"/api/v1/users/{target['id']}/status",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert response.status_code == 422


def test_users_invitation_and_permission_template_contracts() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Admin Templates",
        email="admin.templates@example.com",
        role="admin",
    )

    invitation = client.post(
        "/api/v1/users/invitations",
        json={
            "full_name": "Invited Teacher",
            "email": "invited.teacher@example.com",
            "role": "teacher",
            "extended_roles": ["year_head"],
            "expires_in_days": 7,
        },
        headers=headers,
    )
    assert invitation.status_code == 201, invitation.text
    invitation_payload = invitation.json()
    assert invitation_payload["status"] == "pending"
    assert invitation_payload["email"] == "invited.teacher@example.com"
    listed_invitations = client.get("/api/v1/users/invitations", headers=headers)
    assert listed_invitations.status_code == 200, listed_invitations.text
    assert any(item["email"] == "invited.teacher@example.com" for item in listed_invitations.json())

    builtin_templates = client.get("/api/v1/users/permission-templates", headers=headers)
    assert builtin_templates.status_code == 200, builtin_templates.text
    assert any(
        item["name"] == "Class Representative (CR)"
        and item["role"] == "student"
        for item in builtin_templates.json()
    )

    template = client.post(
        "/api/v1/users/permission-templates",
        json={
            "name": "Teacher Year Head Template",
            "description": "Template for teacher year-head permission",
            "role": "teacher",
            "extended_roles": ["year_head"],
            "role_scope": {},
        },
        headers=headers,
    )
    assert template.status_code == 201, template.text
    template_payload = template.json()
    assert template_payload["name"] == "Teacher Year Head Template"
    assert template_payload["role"] == "teacher"

    updated = client.patch(
        f"/api/v1/users/permission-templates/{template_payload['id']}",
        json={"description": "Updated description"},
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["description"] == "Updated description"

    cr_template = client.post(
        "/api/v1/users/permission-templates",
        json={
            "name": "Student CR Generic Template",
            "description": "Generic CR preset without seat binding",
            "role": "student",
            "extended_roles": ["class_representative"],
            "role_scope": {},
        },
        headers=headers,
    )
    assert cr_template.status_code == 201, cr_template.text
    assert cr_template.json()["extended_roles"] == ["class_representative"]
    assert cr_template.json()["role_scope"].get("class_representative") is None

    deleted = client.delete(f"/api/v1/users/permission-templates/{template_payload['id']}", headers=headers)
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["message"] == "Template deleted"


def test_users_export_csv_and_import_preview_contracts() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Admin Import Export",
        email="admin.import-export@example.com",
        role="admin",
    )
    _seed_admin_list_rows(fake_db)

    exported = client.get("/api/v1/users/export.csv", headers=headers)
    assert exported.status_code == 200, exported.text
    assert "text/csv" in exported.headers.get("content-type", "")
    decoded = exported.content.decode("utf-8")
    assert "full_name,email,role,admin_type,is_active" in decoded

    csv_bytes = (
        "full_name,email,role,admin_type,extended_roles\n"
        "Preview Teacher,preview.teacher@example.com,teacher,,year_head\n"
        "Preview Student,preview.student@example.com,student,,club_president\n"
    ).encode("utf-8")
    preview = client.post(
        "/api/v1/users/import/preview",
        files={"file": ("users.csv", csv_bytes, "text/csv")},
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    preview_payload = preview.json()
    assert preview_payload["total_rows"] == 2
    assert preview_payload["valid_rows"] >= 1
    assert "rows" in preview_payload


def test_users_create_and_invitation_accept_role_scope_single_step() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    section_id = ObjectId()
    fake_db.classes.items.append(
        {
            "_id": section_id,
            "name": "Section Scope A",
            "faculty_id": "faculty-1",
            "department_id": "department-1",
            "program_id": "program-1",
            "specialization_id": "spec-1",
            "batch_id": "batch-1",
            "semester_id": "semester-1",
            "class_coordinator_user_id": None,
        }
    )

    _admin, headers = _register_and_login(
        client,
        full_name="Admin Scope",
        email="admin.scope@example.com",
        role="admin",
    )

    created = client.post(
        "/api/v1/users/",
        json={
            "full_name": "Scoped Teacher",
            "email": "scoped.teacher@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
            "role_scope": {"class_coordinator": {"class_id": str(section_id)}},
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    created_payload = created.json()
    assert created_payload["role_scope"]["class_coordinator"]["class_id"] == str(section_id)
    assert any(
        str(item.get("_id")) == str(section_id) and item.get("class_coordinator_user_id") == created_payload["id"]
        for item in fake_db.classes.items
    )

    invitation = client.post(
        "/api/v1/users/invitations",
        json={
            "full_name": "Scoped Invitee",
            "email": "scoped.invitee@example.com",
            "role": "student",
            "extended_roles": ["club_president"],
            "role_scope": {"club_president": {"club_id": "club-42"}},
            "expires_in_days": 7,
        },
        headers=headers,
    )
    assert invitation.status_code == 201, invitation.text
    invitation_payload = invitation.json()
    assert invitation_payload["role_scope"]["club_president"]["club_id"] == "club-42"


def test_users_admin_list_returns_304_with_matching_etag() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    _admin, headers = _register_and_login(
        client,
        full_name="Admin Etag",
        email="admin.etag@example.com",
        role="admin",
    )
    _seed_admin_list_rows(fake_db)

    previous_value = settings.users_capability_http_cache_validation_enabled
    settings.users_capability_http_cache_validation_enabled = True
    try:
        first = client.get("/api/v1/users/admin/list", headers=headers)
        assert first.status_code == 200, first.text
        etag = first.headers.get("etag")
        assert etag

        second = client.get(
            "/api/v1/users/admin/list",
            headers={**headers, "If-None-Match": etag},
        )
        assert second.status_code == 304
    finally:
        settings.users_capability_http_cache_validation_enabled = previous_value
