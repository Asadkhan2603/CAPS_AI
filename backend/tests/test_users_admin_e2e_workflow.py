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


def test_users_admin_end_to_end_workflow() -> None:
    fake_db = _setup_fake_db()
    _ensure_users_admin_collections(fake_db)
    client = TestClient(app)

    admin, admin_headers = _register_and_login(
        client,
        full_name="Workflow Admin",
        email="workflow.admin@example.com",
        role="admin",
    )
    assert admin["role"] == "admin"

    # View users workspace list.
    listed = client.get("/api/v1/users/admin/list", headers=admin_headers)
    assert listed.status_code == 200, listed.text
    assert "items" in listed.json()

    # Add user.
    created = client.post(
        "/api/v1/users/",
        json={
            "full_name": "Workflow Teacher",
            "email": "workflow.teacher@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["year_head"],
        },
        headers=admin_headers,
    )
    assert created.status_code == 201, created.text
    user_id = created.json()["id"]

    # Search/filter user in admin list.
    filtered = client.get("/api/v1/users/admin/list", params={"q": "workflow", "roles": "teacher"}, headers=admin_headers)
    assert filtered.status_code == 200, filtered.text
    assert any(item["email"] == "workflow.teacher@example.com" for item in filtered.json()["items"])

    # Edit safe fields.
    updated_profile = client.patch(
        f"/api/v1/users/{user_id}/profile",
        json={
            "full_name": "Workflow Teacher Updated",
            "department": "Engineering",
            "designation": "Senior Lecturer",
            "change_reason": "End-to-end update",
        },
        headers=admin_headers,
    )
    assert updated_profile.status_code == 200, updated_profile.text
    assert updated_profile.json()["full_name"] == "Workflow Teacher Updated"

    # Edit permissions.
    updated_permissions = client.patch(
        f"/api/v1/users/{user_id}/extensions",
        json={
            "extended_roles": ["year_head"],
            "role_scope": {},
            "change_reason": "End-to-end permission update",
        },
        headers=admin_headers,
    )
    assert updated_permissions.status_code == 200, updated_permissions.text
    assert "year_head" in updated_permissions.json()["extended_roles"]

    # Deactivate/reactivate flow with reason.
    deactivated = client.patch(
        f"/api/v1/users/{user_id}/status",
        json={"is_active": False, "reason": "Policy enforcement"},
        headers=admin_headers,
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["is_active"] is False
    reactivated = client.patch(
        f"/api/v1/users/{user_id}/status",
        json={"is_active": True, "reason": "Reinstated after review"},
        headers=admin_headers,
    )
    assert reactivated.status_code == 200, reactivated.text
    assert reactivated.json()["is_active"] is True

    # Bulk status update.
    bulk_status = client.post(
        "/api/v1/users/bulk/status",
        json={"user_ids": [user_id], "is_active": False, "reason": "Bulk lifecycle operation"},
        headers=admin_headers,
    )
    assert bulk_status.status_code == 200, bulk_status.text
    assert bulk_status.json()["updated_count"] == 1

    # Bulk permission update.
    bulk_permissions = client.patch(
        "/api/v1/users/bulk/extensions",
        json={
            "updates": [
                {"user_id": user_id, "extended_roles": ["year_head"], "role_scope": {}},
            ],
            "change_reason": "Bulk permission operation",
        },
        headers=admin_headers,
    )
    assert bulk_permissions.status_code == 200, bulk_permissions.text
    assert bulk_permissions.json()["updated_count"] == 1

    # Invite flow.
    invited = client.post(
        "/api/v1/users/invitations",
        json={
            "full_name": "Workflow Invitee",
            "email": "workflow.invitee@example.com",
            "role": "teacher",
            "extended_roles": [],
            "expires_in_days": 7,
        },
        headers=admin_headers,
    )
    assert invited.status_code == 201, invited.text
    invitations_list = client.get("/api/v1/users/invitations", headers=admin_headers)
    assert invitations_list.status_code == 200, invitations_list.text
    assert any(item["email"] == "workflow.invitee@example.com" for item in invitations_list.json())

    # Export flow.
    exported = client.get("/api/v1/users/export.csv", headers=admin_headers)
    assert exported.status_code == 200, exported.text
    assert "text/csv" in exported.headers.get("content-type", "")

    # Import preview and commit (invite mode).
    csv_bytes = (
        "full_name,email,role,admin_type,extended_roles\n"
        "Import One,import.one@example.com,teacher,,year_head\n"
    ).encode("utf-8")
    preview = client.post(
        "/api/v1/users/import/preview",
        files={"file": ("users.csv", csv_bytes, "text/csv")},
        headers=admin_headers,
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid_rows"] == 1

    commit = client.post(
        "/api/v1/users/import/commit",
        json={
            "mode": "invite",
            "rows": [
                {
                    "full_name": "Import One",
                    "email": "import.one@example.com",
                    "role": "teacher",
                    "extended_roles": ["year_head"],
                }
            ],
        },
        headers=admin_headers,
    )
    assert commit.status_code == 200, commit.text
    assert commit.json()["mode"] == "invite"
    assert commit.json()["invited_count"] == 1
