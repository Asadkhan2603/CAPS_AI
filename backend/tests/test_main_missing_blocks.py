import asyncio
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.observability import observability_state
from app.main import app
from app.services import background_jobs as background_jobs_service
from app.services import communication_digests as communication_digests_service
from app.services import communication_delivery_retry as communication_delivery_retry_service
from app.services import notifications as notifications_service
from app.services.scheduler import app_scheduler
from app.services import system_health_snapshots as snapshot_service
from tests.test_auth import _create_section_payload, _seed_canonical_structure, _setup_fake_db


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


def _student_headers(client: TestClient, email: str) -> dict:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student User",
            "email": email,
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_submission(client: TestClient, admin_headers: dict, student_email: str, *, title: str = "Eval Assignment"):
    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": title, "description": "Desc", "total_marks": 100},
        headers=admin_headers,
    )
    assert assignment.status_code == 201
    student_headers = _student_headers(client, student_email)
    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"], "notes": "submission"},
        files={"file": ("report.txt", b"machine learning report content", "text/plain")},
        headers=student_headers,
    )
    assert upload.status_code == 201
    return assignment.json(), upload.json(), student_headers


def test_evaluation_create_computes_totals_and_grade() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_eval@example.com")

    _assignment, upload, _student_headers_unused = _create_submission(
        client, headers, "student_eval@example.com", title="Lab 1"
    )

    created = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": upload["id"],
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


def test_evaluation_grade_boundaries() -> None:
    _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_eval_boundaries@example.com")

    _a1, sub1, _s1 = _create_submission(client, headers, "student_eval_a_plus@example.com", title="A Plus")
    _a2, sub2, _s2 = _create_submission(client, headers, "student_eval_a@example.com", title="A Grade")
    _a3, sub3, _s3 = _create_submission(client, headers, "student_eval_need@example.com", title="Need Grade")

    a_plus = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": sub1["id"],
            "attendance_percent": 95,
            "skill": 2.5,
            "behavior": 2.5,
            "report": 10,
            "viva": 20,
            "final_exam": 60,
            "is_finalized": False,
        },
        headers=headers,
    )
    assert a_plus.status_code == 201
    assert a_plus.json()["grand_total"] == 100.0
    assert a_plus.json()["grade"] == "A+"

    a_grade = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": sub2["id"],
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 50,
            "is_finalized": False,
        },
        headers=headers,
    )
    assert a_grade.status_code == 201
    assert a_grade.json()["grand_total"] == 82.0
    assert a_grade.json()["grade"] == "A"

    needs = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": sub3["id"],
            "attendance_percent": 65,
            "skill": 0.5,
            "behavior": 0.5,
            "report": 4,
            "viva": 5,
            "final_exam": 30,
            "is_finalized": False,
        },
        headers=headers,
    )
    assert needs.status_code == 201
    assert needs.json()["grand_total"] == 40.0
    assert needs.json()["grade"] == "Needs Improvement"


def test_finalized_evaluation_is_read_only_except_admin_override() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_eval_finalize@example.com")
    teacher_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher Eval",
            "email": "teacher_eval_finalize@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher_register.status_code == 201
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_eval_finalize@example.com", "password": "password123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Finalize Flow", "description": "Desc", "total_marks": 100},
        headers=teacher_headers,
    )
    assert assignment.status_code == 201
    student_headers = _student_headers(client, "student_eval_finalize@example.com")
    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("report.txt", b"evaluation finalize content", "text/plain")},
        headers=student_headers,
    )
    assert upload.status_code == 201

    created = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": upload.json()["id"],
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 50,
            "is_finalized": False,
        },
        headers=teacher_headers,
    )
    assert created.status_code == 201
    evaluation_id = created.json()["id"]

    finalized = client.patch(f"/api/v1/evaluations/{evaluation_id}/finalize", headers=teacher_headers)
    assert finalized.status_code == 200
    assert finalized.json()["is_finalized"] is True

    teacher_update = client.put(
        f"/api/v1/evaluations/{evaluation_id}",
        json={"remarks": "teacher update after finalize"},
        headers=teacher_headers,
    )
    assert teacher_update.status_code == 403

    admin_update = client.put(
        f"/api/v1/evaluations/{evaluation_id}",
        json={"remarks": "admin override update"},
        headers=admin_headers,
    )
    assert admin_update.status_code == 200

    reopened = client.patch(
        f"/api/v1/evaluations/{evaluation_id}/override-unfinalize",
        json={"reason": "Approved after moderation review"},
        headers=admin_headers,
    )
    assert reopened.status_code == 200
    assert reopened.json()["is_finalized"] is False


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

    student_one_headers = _student_headers(client, "student_similarity_one@example.com")
    student_two_headers = _student_headers(client, "student_similarity_two@example.com")

    first = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("one.txt", b"deep learning and neural networks", "text/plain")},
        headers=student_one_headers,
    )
    second = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("two.txt", b"deep learning and neural networks basics", "text/plain")},
        headers=student_two_headers,
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

    unread_before = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_before.status_code == 200
    assert unread_before.json()["count"] == 1

    listed = client.get("/api/v1/notifications/", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    marked = client.patch(f"/api/v1/notifications/{notification_id}/read", headers=headers)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True

    unread_after = client.get("/api/v1/notifications/unread-count", headers=headers)
    assert unread_after.status_code == 200
    assert unread_after.json()["count"] == 0


def test_targeted_notification_tracks_delivery_ledger_email_and_read_receipt() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_notification_delivery@example.com")

    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Delivery Student",
            "email": "student_notification_delivery@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_register.status_code == 201

    async def fake_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
        _ = (subject, body)
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "sent",
                "error": None,
                "sent_at": datetime.now(timezone.utc),
            }
            for recipient in recipients
        ]

    original_send_email_batch = notifications_service.send_outbound_email_batch
    notifications_service.send_outbound_email_batch = fake_send_email_batch
    try:
        created = client.post(
            "/api/v1/notifications/",
            json={
                "title": "Account Review",
                "message": "Please confirm your profile details.",
                "priority": "normal",
                "scope": "system",
                "target_user_id": student_register.json()["id"],
            },
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["delivery_summary"]["total_recipients"] == 1
        assert body["delivery_summary"]["email"]["sent_count"] == 1
        assert body["delivery_summary"]["read_count"] == 0

        source_rows = [row for row in fake_db.communication_deliveries.items if row.get("source_kind") == "notification"]
        assert len(source_rows) == 2
        assert {row.get("channel") for row in source_rows} == {"in_app", "email"}

        student_login = client.post(
            "/api/v1/auth/login",
            json={"email": "student_notification_delivery@example.com", "password": "password123"},
        )
        assert student_login.status_code == 200
        student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

        listed = client.get("/api/v1/notifications/", headers=student_headers)
        assert listed.status_code == 200
        assert len(listed.json()) == 1
        assert listed.json()[0]["is_read"] is False

        marked = client.patch(f"/api/v1/notifications/{body['id']}/read", headers=student_headers)
        assert marked.status_code == 200
        assert marked.json()["is_read"] is True
        assert marked.json()["delivery_summary"]["read_count"] == 1
        assert marked.json()["delivery_summary"]["unread_count"] == 0

        in_app_row = next(
            row
            for row in fake_db.communication_deliveries.items
            if row.get("source_kind") == "notification" and row.get("channel") == "in_app"
        )
        assert in_app_row["status"] == "read"
        assert in_app_row["read_at"] is not None
    finally:
        notifications_service.send_outbound_email_batch = original_send_email_batch


def test_notice_fanout_records_delivery_ledger_email_status_and_read_summary() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_notice_delivery@example.com")
    student_headers = _student_headers(client, "student_notice_delivery@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="NDLV", start_year=2024, semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Notice Delivery Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201

    student_doc_id = ObjectId()
    fake_db.students.items.append(
        {
            "_id": student_doc_id,
            "full_name": "Delivery Student",
            "roll_number": "NDLV-001",
            "email": "student_notice_delivery@example.com",
            "class_id": section.json()["id"],
            "is_active": True,
        }
    )
    fake_db.enrollments.items.append(
        {
            "_id": ObjectId(),
            "student_id": str(student_doc_id),
            "class_id": section.json()["id"],
        }
    )

    async def fake_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
        _ = (subject, body)
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "sent",
                "error": None,
                "sent_at": datetime.now(timezone.utc),
            }
            for recipient in recipients
        ]

    original_send_email_batch = background_jobs_service.send_outbound_email_batch
    background_jobs_service.send_outbound_email_batch = fake_send_email_batch
    try:
        created = client.post(
            "/api/v1/notices/",
            json={
                "title": "Lab Window",
                "message": "Submit your lab report before Friday.",
                "priority": "urgent",
                "scope": "class",
                "scope_ref_id": section.json()["id"],
            },
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text

        asyncio.run(background_jobs_service.fanout_notice_notifications(created.json()["id"]))

        notice_row = next(item for item in fake_db.notices.items if str(item["_id"]) == created.json()["id"])
        assert notice_row["fanout_status"] == "dispatched"
        assert notice_row["fanout_count"] == 1

        delivery_rows = [row for row in fake_db.communication_deliveries.items if row.get("source_kind") == "notice"]
        assert len(delivery_rows) == 2
        assert {row.get("channel") for row in delivery_rows} == {"in_app", "email"}

        student_notices = client.get("/api/v1/notices/", headers=student_headers)
        assert student_notices.status_code == 200
        assert len(student_notices.json()) == 1
        student_notice = student_notices.json()[0]
        assert student_notice["delivery_summary"]["total_recipients"] == 1
        assert student_notice["delivery_summary"]["email"]["sent_count"] == 1
        assert student_notice["delivery_summary"]["read_count"] == 0

        marked = client.post(f"/api/v1/notices/{student_notice['id']}/read", headers=student_headers)
        assert marked.status_code == 200
        assert marked.json()["is_read"] is True
        assert marked.json()["delivery_summary"]["read_count"] == 1
        assert marked.json()["delivery_summary"]["unread_count"] == 0
    finally:
        background_jobs_service.send_outbound_email_batch = original_send_email_batch


def test_scheduled_notice_dispatch_retries_then_succeeds() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    _admin_headers(client, "admin_scheduled_retry@example.com")
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Scheduled Student",
            "email": "student_scheduled_retry@example.com",
            "password": "password123",
            "role": "student",
        },
    )

    notice_id = ObjectId()
    now = datetime.now(timezone.utc)
    fake_db.notices.items.append(
        {
            "_id": notice_id,
            "title": "Scheduled Retry Notice",
            "message": "Retry this scheduled notice.",
            "priority": "normal",
            "scope": "college",
            "scope_ref_id": None,
            "scheduled_at": now - timedelta(minutes=5),
            "fanout_status": "scheduled",
            "fanout_attempts": 0,
            "fanout_last_attempt_at": None,
            "fanout_next_retry_at": None,
            "fanout_count": 0,
            "fanout_dispatched_at": None,
            "fanout_failed_at": None,
            "fanout_error": None,
            "fanout_processing_started_at": None,
            "fanout_processing_expires_at": None,
            "is_active": True,
            "created_at": now - timedelta(minutes=10),
        }
    )

    original_send_email_batch = background_jobs_service.send_outbound_email_batch
    original_retry_limit = settings.scheduled_notice_retry_limit
    original_retry_backoff_seconds = settings.scheduled_notice_retry_backoff_seconds
    try:
        settings.scheduled_notice_retry_limit = 3
        settings.scheduled_notice_retry_backoff_seconds = 60

        async def failing_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
            _ = (subject, body, recipients)
            raise RuntimeError("smtp timeout")

        async def successful_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
            _ = (subject, body)
            return [
                {
                    "user_id": recipient.get("user_id"),
                    "email": recipient.get("email"),
                    "status": "sent",
                    "error": None,
                    "sent_at": datetime.now(timezone.utc),
                }
                for recipient in recipients
            ]

        background_jobs_service.send_outbound_email_batch = failing_send_email_batch
        first_dispatch = asyncio.run(background_jobs_service.dispatch_scheduled_notice_notifications(limit=10))
        assert first_dispatch == 0

        stored = fake_db.notices.items[0]
        assert stored["fanout_status"] == "retry_scheduled"
        assert stored["fanout_attempts"] == 1
        assert stored["fanout_next_retry_at"] is not None
        assert stored["fanout_error"] == "smtp timeout"
        assert stored["fanout_processing_expires_at"] is None

        stored["fanout_next_retry_at"] = now - timedelta(seconds=1)
        background_jobs_service.send_outbound_email_batch = successful_send_email_batch
        second_dispatch = asyncio.run(background_jobs_service.dispatch_scheduled_notice_notifications(limit=10))
        assert second_dispatch == 1

        stored = fake_db.notices.items[0]
        assert stored["fanout_status"] == "dispatched"
        assert stored["fanout_attempts"] == 2
        assert stored["fanout_next_retry_at"] is None
        assert stored["fanout_error"] is None
        assert stored["fanout_count"] == 2
        assert len(fake_db.notifications.items) == 2
    finally:
        background_jobs_service.send_outbound_email_batch = original_send_email_batch
        settings.scheduled_notice_retry_limit = original_retry_limit
        settings.scheduled_notice_retry_backoff_seconds = original_retry_backoff_seconds


def test_admin_can_fetch_notice_delivery_details() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_notice_detail@example.com")
    student_headers = _student_headers(client, "student_notice_detail@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="NDTD", start_year=2024, semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Notice Detail Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201

    student_doc_id = ObjectId()
    fake_db.students.items.append(
        {
            "_id": student_doc_id,
            "full_name": "Detail Student",
            "roll_number": "NDTD-001",
            "email": "student_notice_detail@example.com",
            "class_id": section.json()["id"],
            "is_active": True,
        }
    )
    fake_db.enrollments.items.append(
        {"_id": ObjectId(), "student_id": str(student_doc_id), "class_id": section.json()["id"]}
    )

    async def fake_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
        _ = (subject, body)
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "sent",
                "error": None,
                "sent_at": datetime.now(timezone.utc),
            }
            for recipient in recipients
        ]

    original_send_email_batch = background_jobs_service.send_outbound_email_batch
    background_jobs_service.send_outbound_email_batch = fake_send_email_batch
    try:
        created = client.post(
            "/api/v1/notices/",
            json={
                "title": "Detail Notice",
                "message": "Inspect delivery rows",
                "priority": "normal",
                "scope": "class",
                "scope_ref_id": section.json()["id"],
            },
            headers=admin_headers,
        )
        assert created.status_code == 201
        asyncio.run(background_jobs_service.fanout_notice_notifications(created.json()["id"]))

        student_list = client.get("/api/v1/notices/", headers=student_headers)
        assert student_list.status_code == 200
        student_notice_id = student_list.json()[0]["id"]
        marked = client.post(f"/api/v1/notices/{student_notice_id}/read", headers=student_headers)
        assert marked.status_code == 200

        details = client.get(
            f"/api/v1/admin/communication/delivery/notices/{created.json()['id']}",
            headers=admin_headers,
        )
        assert details.status_code == 200, details.text
        body = details.json()
        assert body["source_kind"] == "notice"
        assert body["summary"]["total_recipients"] == 1
        assert body["summary"]["read_count"] == 1
        assert len(body["items"]) == 2
        assert {item["channel"] for item in body["items"]} == {"in_app", "email"}
        assert any(item["status"] == "read" for item in body["items"] if item["channel"] == "in_app")
    finally:
        background_jobs_service.send_outbound_email_batch = original_send_email_batch


def test_admin_can_fetch_notification_delivery_details() -> None:
    _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_notification_detail@example.com")

    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Notification Detail Student",
            "email": "student_notification_detail@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_register.status_code == 201

    async def fake_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
        _ = (subject, body)
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "sent",
                "error": None,
                "sent_at": datetime.now(timezone.utc),
            }
            for recipient in recipients
        ]

    original_send_email_batch = notifications_service.send_outbound_email_batch
    notifications_service.send_outbound_email_batch = fake_send_email_batch
    try:
        created = client.post(
            "/api/v1/notifications/",
            json={
                "title": "Detail Notification",
                "message": "Inspect notification delivery rows",
                "priority": "normal",
                "scope": "system",
                "target_user_id": student_register.json()["id"],
            },
            headers=admin_headers,
        )
        assert created.status_code == 201

        details = client.get(
            f"/api/v1/admin/communication/delivery/notifications/{created.json()['id']}",
            headers=admin_headers,
        )
        assert details.status_code == 200, details.text
        body = details.json()
        assert body["source_kind"] == "notification"
        assert body["summary"]["total_recipients"] == 1
        assert len(body["items"]) == 2
        assert {item["channel"] for item in body["items"]} == {"in_app", "email"}
        assert any(item["target_user_id"] == student_register.json()["id"] for item in body["items"])
    finally:
        notifications_service.send_outbound_email_batch = original_send_email_batch


def test_notification_delivery_respects_email_preference() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_notification_pref@example.com")

    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Preference Notification Student",
            "email": "student_notification_pref@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_register.status_code == 201

    for user in fake_db.users.items:
        if user.get("email") == "student_notification_pref@example.com":
            user["communication_preferences"] = {
                "announcement_email": True,
                "club_announcement_email": True,
                "notification_email": False,
            }

    send_calls: list[list[dict]] = []

    async def fake_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
        _ = (subject, body)
        send_calls.append(recipients)
        return []

    original_send_email_batch = notifications_service.send_outbound_email_batch
    notifications_service.send_outbound_email_batch = fake_send_email_batch
    try:
        created = client.post(
            "/api/v1/notifications/",
            json={
                "title": "Preference Notification",
                "message": "Email should be skipped by preference",
                "priority": "normal",
                "scope": "system",
                "target_user_id": student_register.json()["id"],
            },
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["delivery_summary"]["email"]["sent_count"] == 0
        assert body["delivery_summary"]["email"]["skipped_count"] == 1
        assert send_calls == []

        email_rows = [
            row
            for row in fake_db.communication_deliveries.items
            if row.get("source_kind") == "notification" and row.get("channel") == "email"
        ]
        assert len(email_rows) == 1
        assert email_rows[0]["status"] == "skipped"
        assert email_rows[0]["error"] == "Recipient disabled email notifications for system scope"
    finally:
        notifications_service.send_outbound_email_batch = original_send_email_batch


def test_notification_delivery_can_queue_daily_digest_and_process_it() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_notification_digest@example.com")

    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Digest Student",
            "email": "student_notification_digest@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_register.status_code == 201

    for user in fake_db.users.items:
        if user.get("email") == "student_notification_digest@example.com":
            user["communication_preferences"] = {
                "notification_email_mode": "daily_digest",
                "notification_scope_preferences": {
                    "system": {"email_mode": "daily_digest", "in_app": True},
                },
                "digest_preferences": {
                    "daily_digest_hour_utc": 8,
                    "weekly_digest_day_of_week": 2,
                },
            }

    async def fake_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
        _ = (subject, body)
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "sent",
                "error": None,
                "sent_at": datetime.now(timezone.utc),
            }
            for recipient in recipients
        ]

    original_send_email_batch = communication_digests_service.send_outbound_email_batch
    communication_digests_service.send_outbound_email_batch = fake_send_email_batch
    try:
        created = client.post(
            "/api/v1/notifications/",
            json={
                "title": "Digest Notification",
                "message": "Queue this notification for digest delivery",
                "priority": "normal",
                "scope": "system",
                "target_user_id": student_register.json()["id"],
            },
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text
        body = created.json()
        assert body["delivery_summary"]["email"]["pending_count"] == 1
        assert len(fake_db.communication_digests.items) == 1

        fake_db.communication_digests.items[0]["scheduled_for"] = datetime.now(timezone.utc) - timedelta(minutes=1)

        processed = client.post("/api/v1/admin/communication/digests/process?limit=25", headers=admin_headers)
        assert processed.status_code == 200, processed.text
        assert processed.json()["processed_count"] == 1

        digest_row = fake_db.communication_digests.items[0]
        assert digest_row["status"] == "sent"

        delivery_details = client.get(
            f"/api/v1/admin/communication/delivery/notifications/{created.json()['id']}",
            headers=admin_headers,
        )
        assert delivery_details.status_code == 200, delivery_details.text
        delivery_body = delivery_details.json()
        assert delivery_body["summary"]["email"]["sent_count"] == 1
        assert any(
            item["channel"] == "email"
            and item["status"] == "sent"
            and item["metadata"].get("digest_frequency") == "daily_digest"
            for item in delivery_body["items"]
        )
    finally:
        communication_digests_service.send_outbound_email_batch = original_send_email_batch


def test_admin_delivery_report_and_exports_include_digest_metadata() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_report@example.com")

    notification_id = ObjectId()
    other_notification_id = ObjectId()
    fake_db.notifications.items.append(
        {
            "_id": notification_id,
            "public_id": "NTF-REPORT-001",
            "title": "Digest-ready Notification",
            "message": "Delivery metadata report",
            "scope": "system",
            "created_by": "creator-1",
            "created_at": datetime.now(timezone.utc),
            "is_read": False,
        }
    )
    fake_db.notifications.items.append(
        {
            "_id": other_notification_id,
            "public_id": "NTF-REPORT-002",
            "title": "Other Notification",
            "message": "Other scope row",
            "scope": "ai",
            "created_by": "creator-2",
            "created_at": datetime.now(timezone.utc),
            "is_read": False,
        }
    )
    fake_db.communication_deliveries.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-REPORT-001",
                "target_user_id": "user-1",
                "target_email": "user1@example.com",
                "channel": "email",
                "status": "pending",
                "updated_at": datetime.now(timezone.utc),
                "metadata": {"digest_frequency": "daily_digest", "delivery_mode": "daily_digest"},
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-REPORT-001",
                "target_user_id": "user-1",
                "channel": "in_app",
                "status": "sent",
                "sent_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "metadata": {"scope": "system"},
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(other_notification_id),
                "source_public_id": "NTF-REPORT-002",
                "target_user_id": "user-2",
                "channel": "email",
                "status": "failed",
                "updated_at": datetime.now(timezone.utc),
                "metadata": {"scope": "ai"},
            },
        ]
    )
    fake_db.communication_digests.items.append(
        {
            "_id": ObjectId(),
            "source_kind": "notification",
            "source_id": str(notification_id),
            "digest_frequency": "daily_digest",
            "status": "queued",
            "scheduled_for": datetime.now(timezone.utc) + timedelta(hours=1),
        }
    )

    report = client.get(
        "/api/v1/admin/communication/delivery/report?days=30&source_kind=notification&scope=system&status=pending&created_by=creator-1",
        headers=admin_headers,
    )
    assert report.status_code == 200, report.text
    report_body = report.json()
    assert report_body["total_rows"] == 1
    assert report_body["total_sources"] == 1
    assert report_body["by_channel"]["email"] == 1
    assert report_body["by_scope"]["system"] == 1
    assert report_body["digest"]["queued_total"] == 1
    assert report_body["digest"]["daily_total"] == 1
    assert report_body["creator_rows"][0]["key"] == "creator-1"
    assert report_body["creator_rows"][0]["failed_rate_pct"] == 0
    assert report_body["scope_rows"][0]["key"] == "system"
    assert report_body["email_health"]["total_rows"] == 1
    assert report_body["email_health"]["pending_count"] == 1
    assert report_body["email_health"]["delivered_rate_pct"] == 0

    export_response = client.get(
        f"/api/v1/admin/communication/delivery/notifications/{notification_id}/export",
        headers=admin_headers,
    )
    assert export_response.status_code == 200, export_response.text
    assert "text/csv" in export_response.headers["content-type"]
    assert "metadata" in export_response.text
    assert "daily_digest" in export_response.text
    assert "source_created_by" in export_response.text
    assert "source_scope" in export_response.text

    report_export = client.get(
        "/api/v1/admin/communication/delivery/report/export?days=30&source_kind=notification&scope=system&status=pending&created_by=creator-1",
        headers=admin_headers,
    )
    assert report_export.status_code == 200, report_export.text
    assert "daily_digest" in report_export.text
    assert "creator-1" in report_export.text
    assert "system" in report_export.text
    assert "NTF-REPORT-002" not in report_export.text
    assert "Digest-ready Notification" in report_export.text

    creator_export = client.get(
        "/api/v1/admin/communication/delivery/report/export?days=30&source_kind=notification&scope=system&view=creator_summary",
        headers=admin_headers,
    )
    assert creator_export.status_code == 200, creator_export.text
    assert "failed_rate_pct" in creator_export.text
    assert "creator-1" in creator_export.text

    scope_export = client.get(
        "/api/v1/admin/communication/delivery/report/export?days=30&source_kind=notification&view=scope_summary",
        headers=admin_headers,
    )
    assert scope_export.status_code == 200, scope_export.text
    assert "label" in scope_export.text
    assert "System" in scope_export.text

    email_health_export = client.get(
        "/api/v1/admin/communication/delivery/report/export?days=30&source_kind=notification&view=email_health",
        headers=admin_headers,
    )
    assert email_health_export.status_code == 200, email_health_export.text
    assert "attention_rate_pct" in email_health_export.text
    assert "queued_total" in email_health_export.text


def test_admin_delivery_report_trends_respect_saved_view_filters() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_trends@example.com")

    now = datetime.now(timezone.utc)
    notification_id = ObjectId()
    other_notification_id = ObjectId()
    fake_db.notifications.items.extend(
        [
            {
                "_id": notification_id,
                "public_id": "NTF-TREND-001",
                "title": "System Trend Notification",
                "message": "Trend target",
                "scope": "system",
                "created_by": "creator-trend",
                "created_at": now - timedelta(days=1),
                "is_read": False,
            },
            {
                "_id": other_notification_id,
                "public_id": "NTF-TREND-002",
                "title": "AI Trend Notification",
                "message": "Should be filtered out",
                "scope": "ai",
                "created_by": "creator-other",
                "created_at": now - timedelta(days=1),
                "is_read": False,
            },
        ]
    )
    fake_db.communication_deliveries.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-TREND-001",
                "target_user_id": "user-1",
                "channel": "email",
                "status": "failed",
                "updated_at": now - timedelta(days=1),
                "metadata": {"scope": "system"},
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-TREND-001",
                "target_user_id": "user-2",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
                "metadata": {"scope": "system"},
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(other_notification_id),
                "source_public_id": "NTF-TREND-002",
                "target_user_id": "user-3",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
                "metadata": {"scope": "ai"},
            },
        ]
    )

    response = client.get(
        "/api/v1/admin/communication/delivery/report/trends?days=3&source_kind=notification&scope=system&status=failed&created_by=creator-trend",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["granularity"] == "day"
    assert body["days"] == 3
    assert len(body["points"]) == 3
    assert sum(point["failed_count"] for point in body["points"]) == 2
    assert sum(point["total_count"] for point in body["points"]) == 2
    assert all(point["skipped_count"] == 0 for point in body["points"])


def test_admin_delivery_report_includes_creator_and_scope_comparisons() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_compare@example.com")

    now = datetime.now(timezone.utc)
    notification_ids = [ObjectId(), ObjectId(), ObjectId()]
    fake_db.notifications.items.extend(
        [
            {
                "_id": notification_ids[0],
                "public_id": "NTF-COMP-001",
                "title": "Creator One System",
                "message": "compare",
                "scope": "system",
                "created_by": "creator-one",
                "created_at": now,
                "is_read": False,
            },
            {
                "_id": notification_ids[1],
                "public_id": "NTF-COMP-002",
                "title": "Creator One AI",
                "message": "compare",
                "scope": "ai",
                "created_by": "creator-one",
                "created_at": now,
                "is_read": False,
            },
            {
                "_id": notification_ids[2],
                "public_id": "NTF-COMP-003",
                "title": "Creator Two System",
                "message": "compare",
                "scope": "system",
                "created_by": "creator-two",
                "created_at": now,
                "is_read": False,
            },
        ]
    )
    fake_db.communication_deliveries.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_ids[0]),
                "source_public_id": "NTF-COMP-001",
                "target_user_id": "user-1",
                "channel": "email",
                "status": "sent",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_ids[0]),
                "source_public_id": "NTF-COMP-001",
                "target_user_id": "user-2",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
                "error": "Mailbox unavailable",
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_ids[1]),
                "source_public_id": "NTF-COMP-002",
                "target_user_id": "user-3",
                "channel": "email",
                "status": "pending",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_ids[2]),
                "source_public_id": "NTF-COMP-003",
                "target_user_id": "user-4",
                "channel": "email",
                "status": "skipped",
                "updated_at": now,
                "error": "Recipient disabled email notifications for system scope",
            },
        ]
    )

    response = client.get(
        "/api/v1/admin/communication/delivery/report?days=7&source_kind=notification",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    creator_rows = {item["key"]: item for item in body["creator_rows"]}
    scope_rows = {item["key"]: item for item in body["scope_rows"]}

    assert creator_rows["creator-one"]["total_count"] == 3
    assert creator_rows["creator-one"]["failed_count"] == 1
    assert creator_rows["creator-one"]["pending_count"] == 1
    assert creator_rows["creator-one"]["failed_rate_pct"] == round((1 / 3) * 100, 2)
    assert creator_rows["creator-two"]["skipped_count"] == 1
    assert scope_rows["system"]["total_count"] == 3
    assert scope_rows["ai"]["pending_count"] == 1
    assert body["email_health"]["top_errors"][0]["count"] == 1
    assert body["email_health"]["retry_candidate_count"] == 2


def test_admin_delivery_report_anomalies_detect_failure_spike_and_pending_buildup() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_anomalies@example.com")

    now = datetime.now(timezone.utc)
    notification_id = ObjectId()
    fake_db.notifications.items.append(
        {
            "_id": notification_id,
            "public_id": "NTF-ANOM-001",
            "title": "Anomaly Notification",
            "message": "Anomaly target",
            "scope": "system",
            "created_by": "creator-anomaly",
            "created_at": now - timedelta(days=2),
            "is_read": False,
        }
    )
    fake_db.communication_deliveries.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-1",
                "channel": "email",
                "status": "pending",
                "updated_at": now - timedelta(days=2),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-2",
                "channel": "email",
                "status": "pending",
                "updated_at": now - timedelta(days=1),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-2b",
                "channel": "email",
                "status": "pending",
                "updated_at": now - timedelta(days=1),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-3",
                "channel": "email",
                "status": "pending",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-4",
                "channel": "email",
                "status": "pending",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-5",
                "channel": "email",
                "status": "pending",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-6",
                "channel": "email",
                "status": "failed",
                "updated_at": now - timedelta(days=2),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-7",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-8",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-9",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-001",
                "target_user_id": "user-10",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
            },
        ]
    )

    response = client.get(
        "/api/v1/admin/communication/delivery/report/anomalies?days=3&source_kind=notification&scope=system&created_by=creator-anomaly",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    codes = {item["code"] for item in body["alerts"]}
    assert "delivery.failed_rate_spike" in codes
    assert "delivery.pending_backlog_rising" in codes


def test_admin_can_retry_failed_notice_email_delivery() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_notice_retry@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="NTRY", start_year=2024, semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Notice Retry Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201

    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Retry Student",
            "email": "student_notice_retry@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_register.status_code == 201

    student_doc_id = ObjectId()
    fake_db.students.items.append(
        {
            "_id": student_doc_id,
            "full_name": "Retry Student",
            "roll_number": "NTRY-001",
            "email": "student_notice_retry@example.com",
            "class_id": section.json()["id"],
            "is_active": True,
        }
    )
    fake_db.enrollments.items.append(
        {"_id": ObjectId(), "student_id": str(student_doc_id), "class_id": section.json()["id"]}
    )

    async def failing_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
        _ = (subject, body)
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "failed",
                "error": "SMTP timeout",
                "sent_at": None,
            }
            for recipient in recipients
        ]

    async def successful_send_email_batch(*, subject: str, body: str, recipients: list[dict]) -> list[dict]:
        _ = (subject, body)
        return [
            {
                "user_id": recipient.get("user_id"),
                "email": recipient.get("email"),
                "status": "sent",
                "error": None,
                "sent_at": datetime.now(timezone.utc),
            }
            for recipient in recipients
        ]

    original_notice_send = background_jobs_service.send_outbound_email_batch
    original_retry_send = communication_delivery_retry_service.send_outbound_email_batch
    background_jobs_service.send_outbound_email_batch = failing_send_email_batch
    communication_delivery_retry_service.send_outbound_email_batch = successful_send_email_batch
    try:
        created = client.post(
            "/api/v1/notices/",
            json={
                "title": "Retryable Notice",
                "message": "Initial email delivery fails",
                "priority": "normal",
                "scope": "class",
                "scope_ref_id": section.json()["id"],
            },
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text

        asyncio.run(background_jobs_service.fanout_notice_notifications(created.json()["id"]))

        before_retry = client.get(
            f"/api/v1/admin/communication/delivery/notices/{created.json()['id']}",
            headers=admin_headers,
        )
        assert before_retry.status_code == 200, before_retry.text
        assert before_retry.json()["summary"]["email"]["failed_count"] == 1

        retried = client.post(
            f"/api/v1/admin/communication/delivery/notices/{created.json()['id']}/retry-email",
            json={"include_skipped": True},
            headers=admin_headers,
        )
        assert retried.status_code == 200, retried.text
        body = retried.json()
        assert body["retried_count"] == 1
        assert body["details"]["summary"]["email"]["sent_count"] == 1
        assert body["details"]["summary"]["email"]["failed_count"] == 0

        email_rows = [
            row
            for row in fake_db.communication_deliveries.items
            if row.get("source_kind") == "notice" and row.get("channel") == "email"
        ]
        assert len(email_rows) == 1
        assert email_rows[0]["status"] == "sent"
    finally:
        background_jobs_service.send_outbound_email_batch = original_notice_send
        communication_delivery_retry_service.send_outbound_email_batch = original_retry_send


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


def test_ai_evaluation_pipeline_persists_feedback_and_is_traceable() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_ai_pipeline@example.com")

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "AI Pipeline Assignment", "description": "Desc", "total_marks": 100},
        headers=admin_headers,
    )
    assert assignment.status_code == 201

    student_headers = _student_headers(client, "student_ai_pipeline@example.com")
    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"], "notes": "ai pipeline"},
        files={"file": ("report.txt", b"ai generated rubric text for testing", "text/plain")},
        headers=student_headers,
    )
    assert upload.status_code == 201
    submission_id = upload.json()["id"]

    ai_result = client.post(f"/api/v1/submissions/{submission_id}/ai-evaluate", headers=admin_headers)
    assert ai_result.status_code == 200
    ai_body = ai_result.json()
    assert ai_body["ai_status"] in ["fallback", "completed"]
    assert ai_body["ai_score"] is not None
    assert ai_body["ai_feedback"]

    evaluation = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission_id,
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 50,
            "is_finalized": False,
        },
        headers=admin_headers,
    )
    assert evaluation.status_code == 201
    eval_body = evaluation.json()
    assert eval_body["ai_score"] == ai_body["ai_score"]
    assert eval_body["ai_feedback"] == ai_body["ai_feedback"]

    submission_audit = [
        item for item in fake_db.audit_logs.items
        if item.get("entity_type") == "submission"
        and item.get("entity_id") == submission_id
        and item.get("action") == "ai_evaluate"
    ]
    assert len(submission_audit) == 1


def test_similarity_threshold_alerts_generate_logs_notifications_and_scope_views() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_similarity_alerts@example.com")
    owner_teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner Teacher",
            "email": "owner_similarity_alerts@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    coordinator_teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator Teacher",
            "email": "coord_similarity_alerts@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    plain_teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Plain Teacher",
            "email": "plain_similarity_alerts@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert owner_teacher.status_code == 201
    assert coordinator_teacher.status_code == 201
    assert plain_teacher.status_code == 201

    structure = _seed_canonical_structure(fake_db, suffix="SIMA")
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="BCA FY",
            class_coordinator_user_id=coordinator_teacher.json()["id"],
        ),
        headers=admin_headers,
    )
    assert class_item.status_code == 201

    owner_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner_similarity_alerts@example.com", "password": "password123"},
    )
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    assignment = client.post(
        "/api/v1/assignments/",
        json={
            "title": "Similarity Alert Assignment",
            "description": "desc",
            "class_id": class_item.json()["id"],
            "total_marks": 100,
        },
        headers=owner_headers,
    )
    assert assignment.status_code == 201

    student_one_headers = _student_headers(client, "student_sim_alerts_one@example.com")
    student_two_headers = _student_headers(client, "student_sim_alerts_two@example.com")
    first = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("one.txt", b"identical report text similarity test", "text/plain")},
        headers=student_one_headers,
    )
    second = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("two.txt", b"identical report text similarity test", "text/plain")},
        headers=student_two_headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    run = client.post(
        f"/api/v1/similarity/checks/run/{first.json()['id']}?threshold=0.1",
        headers=owner_headers,
    )
    assert run.status_code == 200
    checks = run.json()
    assert len(checks) >= 1
    assert checks[0]["is_flagged"] is True
    assert checks[0]["score"] >= 0.1
    assert checks[0]["source_assignment_id"] == assignment.json()["id"]

    assert len(fake_db.notifications.items) >= 1
    assert any(item.get("priority") == "urgent" for item in fake_db.notifications.items)

    coord_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_similarity_alerts@example.com", "password": "password123"},
    )
    coord_headers = {"Authorization": f"Bearer {coord_login.json()['access_token']}"}
    coord_view = client.get("/api/v1/similarity/checks?is_flagged=true", headers=coord_headers)
    assert coord_view.status_code == 200
    assert len(coord_view.json()) >= 1

    plain_login = client.post(
        "/api/v1/auth/login",
        json={"email": "plain_similarity_alerts@example.com", "password": "password123"},
    )
    plain_headers = {"Authorization": f"Bearer {plain_login.json()['access_token']}"}
    plain_view = client.get("/api/v1/similarity/checks?is_flagged=true", headers=plain_headers)
    assert plain_view.status_code == 200
    assert len(plain_view.json()) == 0


def test_teacher_controls_plagiarism_toggle_and_similarity_respects_it() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_toggle_plagiarism@example.com")
    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher Toggle",
            "email": "teacher_toggle_plagiarism@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_toggle_plagiarism@example.com", "password": "password123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Plagiarism Switch", "description": "desc", "total_marks": 100},
        headers=teacher_headers,
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]

    admin_toggle = client.patch(
        f"/api/v1/assignments/{assignment_id}/plagiarism",
        json={"plagiarism_enabled": False},
        headers=admin_headers,
    )
    assert admin_toggle.status_code == 403

    teacher_toggle = client.patch(
        f"/api/v1/assignments/{assignment_id}/plagiarism",
        json={"plagiarism_enabled": False},
        headers=teacher_headers,
    )
    assert teacher_toggle.status_code == 200
    assert teacher_toggle.json()["plagiarism_enabled"] is False

    student_one_headers = _student_headers(client, "student_toggle_one@example.com")
    student_two_headers = _student_headers(client, "student_toggle_two@example.com")
    first = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("one.txt", b"same text", "text/plain")},
        headers=student_one_headers,
    )
    second = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("two.txt", b"same text", "text/plain")},
        headers=student_two_headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    blocked = client.post(
        f"/api/v1/similarity/checks/run/{first.json()['id']}?threshold=0.1",
        headers=teacher_headers,
    )
    assert blocked.status_code == 400
    assert blocked.json()["detail"] == "Plagiarism detection is disabled for this assignment"


def test_reopen_ticket_flow_requires_reason_and_admin_approval() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_reopen_flow@example.com")
    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher Reopen",
            "email": "teacher_reopen_flow@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_reopen_flow@example.com", "password": "password123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Reopen Assignment", "description": "desc", "total_marks": 100},
        headers=teacher_headers,
    )
    student_headers = _student_headers(client, "student_reopen_flow@example.com")
    submission = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("report.txt", b"reopen flow text", "text/plain")},
        headers=student_headers,
    )
    assert submission.status_code == 201

    evaluation = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission.json()["id"],
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 50,
            "is_finalized": False,
        },
        headers=teacher_headers,
    )
    assert evaluation.status_code == 201
    eval_id = evaluation.json()["id"]

    finalized = client.patch(f"/api/v1/evaluations/{eval_id}/finalize", headers=teacher_headers)
    assert finalized.status_code == 200
    assert finalized.json()["is_finalized"] is True

    ticket_bad = client.post(
        "/api/v1/review-tickets/",
        json={"evaluation_id": eval_id, "reason": "bad"},
        headers=teacher_headers,
    )
    assert ticket_bad.status_code == 422

    ticket = client.post(
        "/api/v1/review-tickets/",
        json={"evaluation_id": eval_id, "reason": "Need correction for verified attendance mismatch"},
        headers=teacher_headers,
    )
    assert ticket.status_code == 201
    ticket_id = ticket.json()["id"]

    approved = client.patch(
        f"/api/v1/review-tickets/{ticket_id}/approve",
        json={"reason": "Approved after evidence verification"},
        headers=admin_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    updated_eval = client.get(f"/api/v1/evaluations/{eval_id}", headers=teacher_headers)
    assert updated_eval.status_code == 200
    assert updated_eval.json()["is_finalized"] is False
    assert len(fake_db.review_tickets.items) == 1


def test_teacher_analytics_summary_does_not_leak_admin_global_counts() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_analytics_role@example.com")
    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher Metrics",
            "email": "teacher_analytics_role@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_analytics_role@example.com", "password": "password123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    client.post(
        "/api/v1/assignments/",
        json={"title": "Teacher Metric Assignment", "description": "desc", "total_marks": 100},
        headers=teacher_headers,
    )

    teacher_summary = client.get("/api/v1/analytics/summary", headers=teacher_headers)
    assert teacher_summary.status_code == 200
    summary = teacher_summary.json()["summary"]
    assert "my_assignments" in summary
    assert "users" not in summary
    assert "courses" not in summary

    admin_summary = client.get("/api/v1/analytics/summary", headers=admin_headers)
    assert admin_summary.status_code == 200
    assert "users" in admin_summary.json()["summary"]


def test_urgent_notice_with_expiry_filters_out_after_expiry() -> None:
    _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_notice_expiry@example.com")

    from datetime import datetime, timedelta, timezone

    expired = client.post(
        "/api/v1/notices/",
        json={
            "title": "Expired Urgent",
            "message": "Old urgent notice",
            "priority": "urgent",
            "scope": "college",
            "expires_at": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
        },
        headers=admin_headers,
    )
    active = client.post(
        "/api/v1/notices/",
        json={
            "title": "Active Urgent",
            "message": "Current urgent notice",
            "priority": "urgent",
            "scope": "college",
            "expires_at": (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat(),
        },
        headers=admin_headers,
    )
    assert expired.status_code == 201
    assert active.status_code == 201

    listed = client.get("/api/v1/notices/?priority=urgent", headers=admin_headers)
    assert listed.status_code == 200
    titles = [item["title"] for item in listed.json()]
    assert "Active Urgent" in titles
    assert "Expired Urgent" not in titles


def test_event_registration_blocks_duplicate_and_capacity_overflow() -> None:
    _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_event_reg@example.com")

    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Coding Club", "description": "Club"},
        headers=admin_headers,
    )
    assert club.status_code == 201

    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Hack Sprint",
            "description": "Event",
            "capacity": 1,
        },
        headers=admin_headers,
    )
    assert event.status_code == 201
    event_id = event.json()["id"]

    student_one_headers = _student_headers(client, "student_event_one@example.com")
    student_two_headers = _student_headers(client, "student_event_two@example.com")

    first = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event_id},
        headers=student_one_headers,
    )
    assert first.status_code == 201

    duplicate = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event_id},
        headers=student_one_headers,
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Already registered for this event"

    overflow = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event_id},
        headers=student_two_headers,
    )
    assert overflow.status_code == 400
    assert overflow.json()["detail"] == "Event registration capacity reached"


def test_teacher_ai_chat_evaluation_and_history_flow() -> None:
    _setup_fake_db()
    client = TestClient(app)

    # Avoid live provider calls during test run.
    from app.api.v1.endpoints import ai as ai_endpoint

    original_generate = ai_endpoint.generate_evaluation_chat_reply
    ai_endpoint.generate_evaluation_chat_reply = (
        lambda **kwargs: ("Suggested Marks: 4/5\nExplanation: Good coverage.\nConstructive Feedback: Clear answer.\nImprovement Suggestions: Add one example.", None)
    )
    try:
        teacher = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Teacher AI Chat",
                "email": "teacher_ai_chat@example.com",
                "password": "password123",
                "role": "teacher",
            },
        )
        assert teacher.status_code == 201
        teacher_id = teacher.json()["id"]
        teacher_login = client.post(
            "/api/v1/auth/login",
            json={"email": "teacher_ai_chat@example.com", "password": "password123"},
        )
        teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

        assignment = client.post(
            "/api/v1/assignments/",
            json={"title": "AI Console Assignment", "description": "Q1. Explain OOP.", "total_marks": 100},
            headers=teacher_headers,
        )
        assert assignment.status_code == 201
        exam_id = assignment.json()["id"]

        student_headers = _student_headers(client, "student_ai_chat@example.com")
        student_me = client.get("/api/v1/auth/me", headers=student_headers)
        assert student_me.status_code == 200
        student_id = student_me.json()["id"]

        submission = client.post(
            "/api/v1/submissions/upload",
            data={"assignment_id": exam_id, "notes": "oop answer"},
            files={"file": ("answer.txt", b"OOP uses encapsulation, inheritance and polymorphism.", "text/plain")},
            headers=student_headers,
        )
        assert submission.status_code == 201
        submission_id = submission.json()["id"]

        evaluate = client.post(
            "/api/v1/ai/evaluate",
            json={
                "teacher_id": teacher_id,
                "student_id": student_id,
                "exam_id": exam_id,
                "question_id": "q1",
                "teacher_message": "Evaluate this answer for 5 marks",
                "question_text": "Explain OOP principles.",
                "student_answer": "OOP uses encapsulation, inheritance and polymorphism.",
                "rubric": "Concept clarity, examples, completeness",
                "submission_id": submission_id,
            },
            headers=teacher_headers,
        )
        assert evaluate.status_code == 200
        evaluate_body = evaluate.json()
        assert "ai_response" in evaluate_body
        assert evaluate_body["thread"]["teacher_id"] == teacher_id
        assert len(evaluate_body["thread"]["messages"]) == 2

        history = client.get(f"/api/v1/ai/history/{student_id}/{exam_id}", headers=teacher_headers)
        assert history.status_code == 200
        history_body = history.json()
        assert history_body["student_id"] == student_id
        assert history_body["exam_id"] == exam_id
        assert len(history_body["messages"]) == 2
        assert history_body["messages"][0]["role"] == "teacher"
        assert history_body["messages"][1]["role"] == "ai"
    finally:
        ai_endpoint.generate_evaluation_chat_reply = original_generate


def test_student_cannot_access_ai_chat_endpoints() -> None:
    _setup_fake_db()
    client = TestClient(app)
    student_headers = _student_headers(client, "student_ai_forbidden@example.com")

    blocked_eval = client.post(
        "/api/v1/ai/evaluate",
        json={
            "teacher_id": "t1",
            "student_id": "s1",
            "exam_id": "e1",
            "teacher_message": "test",
            "question_text": "q",
            "student_answer": "a",
            "rubric": "r",
        },
        headers=student_headers,
    )
    assert blocked_eval.status_code == 403

    blocked_history = client.get("/api/v1/ai/history/s1/e1", headers=student_headers)
    assert blocked_history.status_code == 403


def test_admin_system_health_includes_observability_metrics_and_alerts() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_system_metrics@example.com")
    observability_state.reset()

    original_scheduler_state = (
        app_scheduler._enabled,
        app_scheduler._running,
        app_scheduler._is_leader,
    )
    try:
        app_scheduler._enabled = True
        app_scheduler._running = True
        app_scheduler._is_leader = False

        for _ in range(3):
            observability_state.request_started()
            observability_state.record_request(
                method="GET",
                path="/api/v1/test/failing-endpoint",
                status_code=500,
                duration_ms=2100,
            )
        observability_state.request_started()
        observability_state.record_request(
            method="GET",
            path="/api/v1/test/healthy-endpoint",
            status_code=200,
            duration_ms=120,
        )
        observability_state.record_scheduler_job_run(
            job_name="notice_dispatch",
            success=True,
            duration_ms=35,
            processed_count=2,
        )
        for _ in range(4):
            observability_state.record_ai_generation(status="fallback", provider="local")
        observability_state.record_similarity_run(
            candidate_count=850,
            duration_ms=2800,
            flagged_count=3,
            max_score=0.91,
        )
        now = datetime.now(timezone.utc)
        fake_db.ai_jobs.items.extend(
            [
                {
                    "_id": ObjectId(),
                    "status": "queued",
                    "requested_at": now - timedelta(minutes=6),
                },
                {
                    "_id": ObjectId(),
                    "status": "queued",
                    "requested_at": now - timedelta(minutes=1),
                },
                {
                    "_id": ObjectId(),
                    "status": "running",
                    "requested_at": now - timedelta(seconds=30),
                },
                {
                    "_id": ObjectId(),
                    "status": "failed",
                    "requested_at": now - timedelta(minutes=2),
                },
            ]
        )
        fake_db.notices.items.extend(
            [
                {
                    "_id": ObjectId(),
                    "title": "Due Scheduled Notice",
                    "is_active": True,
                    "scheduled_at": now - timedelta(minutes=12),
                    "fanout_status": "scheduled",
                    "fanout_attempts": 0,
                    "fanout_dispatched_at": None,
                    "fanout_next_retry_at": None,
                    "fanout_processing_expires_at": None,
                },
                {
                    "_id": ObjectId(),
                    "title": "Retry Pending Notice",
                    "is_active": True,
                    "scheduled_at": now - timedelta(minutes=15),
                    "fanout_status": "retry_scheduled",
                    "fanout_attempts": 1,
                    "fanout_dispatched_at": None,
                    "fanout_next_retry_at": now + timedelta(minutes=5),
                    "fanout_processing_expires_at": None,
                },
                {
                    "_id": ObjectId(),
                    "title": "In Progress Notice",
                    "is_active": True,
                    "scheduled_at": now - timedelta(minutes=8),
                    "fanout_status": "dispatching",
                    "fanout_attempts": 1,
                    "fanout_dispatched_at": None,
                    "fanout_next_retry_at": None,
                    "fanout_processing_expires_at": now + timedelta(minutes=2),
                },
                {
                    "_id": ObjectId(),
                    "title": "Terminal Failed Notice",
                    "is_active": True,
                    "scheduled_at": now - timedelta(minutes=20),
                    "fanout_status": "failed",
                    "fanout_attempts": 3,
                    "fanout_dispatched_at": None,
                    "fanout_next_retry_at": None,
                    "fanout_processing_expires_at": None,
                },
            ]
        )

        response = client.get("/api/v1/admin/system/health", headers=headers)
        assert response.status_code == 200
        body = response.json()

        assert body["snapshot_served_from"] == "live"
        assert body["snapshot_age_seconds"] == 0
        assert body["alert_count"] >= 2
        assert any(alert["code"] == "http.high_server_error_rate" for alert in body["alerts"])
        assert any(alert["code"] == "scheduler.leader_lock_missing" for alert in body["alerts"])
        assert any(alert["code"] == "ai.oldest_job_age_critical" for alert in body["alerts"])
        assert any(alert["code"] == "ai.fallback_rate_critical" for alert in body["alerts"])
        assert any(alert["code"] == "similarity.high_candidate_count" for alert in body["alerts"])
        assert body["scheduler_lock"]["owner_id"] is None
        assert body["scheduled_notice_dispatch"]["pending_total"] == 4
        assert body["scheduled_notice_dispatch"]["due_now_total"] == 1
        assert body["scheduled_notice_dispatch"]["retry_pending_total"] == 1
        assert body["scheduled_notice_dispatch"]["in_progress_total"] == 1
        assert body["scheduled_notice_dispatch"]["terminal_failed_total"] == 1
        assert body["scheduled_notice_dispatch"]["oldest_due_age_seconds"] >= 720
        assert body["observability"]["request_metrics"]["requests_15m"] >= 4
        assert body["observability"]["request_metrics"]["slow_requests_15m"] >= 3
        assert body["observability"]["request_metrics"]["top_paths_15m"][0]["path"] == "/api/v1/test/failing-endpoint"
        assert body["observability"]["scheduler_metrics"]["jobs"]["notice_dispatch"]["success_total"] >= 1
        assert body["observability"]["scheduler_metrics"]["jobs"]["notice_dispatch"]["processed_total"] >= 2
        assert body["observability"]["ai_metrics"]["queued_jobs"] == 2
        assert body["observability"]["ai_metrics"]["running_jobs"] == 1
        assert body["observability"]["ai_metrics"]["failed_jobs"] == 1
        assert body["observability"]["ai_metrics"]["oldest_queued_age_seconds"] >= 360
        assert body["observability"]["ai_metrics"]["fallbacks_15m"] == 4
        assert body["observability"]["ai_metrics"]["fallback_rate_pct_15m"] == 100.0
        assert body["observability"]["ai_metrics"]["last_similarity_candidate_count"] == 850
        assert len(body["observability"]["ai_metrics"]["history_15m"]) >= 3
        assert any(point["queued_jobs"] == 2 for point in body["observability"]["ai_metrics"]["history_15m"])
        assert any(point["similarity_candidate_count"] == 850 for point in body["observability"]["ai_metrics"]["history_15m"])
        assert len(body["snapshot_history"]) >= 1
        assert body["snapshot_history"][0]["queued_jobs"] == 2
        assert body["snapshot_history"][0]["fallback_rate_pct_15m"] == 100.0
        assert body["snapshot_history"][0]["retained_rows"] == 1
        assert body["snapshot_history"][0]["last_pruned_deleted_count"] == 0
        assert body["snapshot_history"][0]["is_within_retention_bound"] is True
        assert body["clubs_observability"]["summary"]["retention_days"] >= 7
        assert "hourly_24h" in body["clubs_observability"]
        assert "daily_14d" in body["clubs_observability"]
        assert "recent_pressure_windows" in body["clubs_observability"]
        assert body["snapshot_store"]["retained_rows"] == 1
        assert body["snapshot_store"]["is_within_retention_bound"] is True
        assert body["snapshot_store"]["retention_minutes"] >= 60
        assert body["snapshot_store"]["retention_days"] >= 7
        assert body["snapshot_store"]["last_pruned_deleted_count"] == 0
        assert body["alert_routing"]["enabled"] is True
        assert body["alert_routing"]["target_user_count"] == 1
        assert body["alert_routing"]["active_alert_count"] >= 1
        assert body["alert_routing"]["notifications_created"] >= 1
        assert "http.high_server_error_rate" in body["alert_routing"]["routed_alert_codes"]
        assert len(body["alert_route_history"]) >= 1
        high_error_route = next((row for row in body["alert_route_history"] if row["alert_code"] == "http.high_server_error_rate"), None)
        assert high_error_route is not None
        assert high_error_route["routed_count"] >= 1
        assert high_error_route["notifications_sent_total"] >= 1
        assert any(entry["action"] == "routed" for entry in high_error_route["history"])
        assert len(fake_db.notifications.items) >= 1
        assert all(item["scope"] == "system" for item in fake_db.notifications.items)
        notification_count_after_first_call = len(fake_db.notifications.items)
        second = client.get("/api/v1/admin/system/health", headers=headers)
        assert second.status_code == 200
        second_body = second.json()
        assert second_body["snapshot_served_from"] == "snapshot"
        assert second_body["snapshot_age_seconds"] >= 0
        assert second_body["alert_routing"]["notifications_created"] == 0
        assert len(fake_db.notifications.items) == notification_count_after_first_call
        assert len(fake_db.system_health_snapshots.items) == 1
        assert len(fake_db.operational_alert_routes.items) >= 1
        third = client.get("/api/v1/admin/system/health?refresh=true", headers=headers)
        assert third.status_code == 200
        third_body = third.json()
        assert third_body["snapshot_served_from"] == "live"
        assert third_body["alert_routing"]["notifications_created"] == 0
        assert len(third_body["alert_route_history"]) >= 1
        third_high_error_route = next((row for row in third_body["alert_route_history"] if row["alert_code"] == "http.high_server_error_rate"), None)
        assert third_high_error_route is not None
        assert third_high_error_route["cooldown_suppressed_count"] >= 1
        assert third_high_error_route["last_routing_outcome"] == "cooldown_suppressed"
        assert len(fake_db.notifications.items) == notification_count_after_first_call
        assert fake_db.scheduler_locks.items == []
    finally:
        app_scheduler._enabled, app_scheduler._running, app_scheduler._is_leader = original_scheduler_state
        observability_state.reset()


def test_admin_system_health_normalizes_naive_scheduler_lock_datetimes() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_system_lock_tz@example.com")

    original_scheduler_state = (
        app_scheduler._enabled,
        app_scheduler._running,
        app_scheduler._is_leader,
    )
    try:
        app_scheduler._enabled = True
        app_scheduler._running = True
        app_scheduler._is_leader = True
        naive_expires_at = (datetime.now(timezone.utc) - timedelta(minutes=5)).replace(tzinfo=None)
        naive_heartbeat_at = (datetime.now(timezone.utc) - timedelta(minutes=1)).replace(tzinfo=None)
        fake_db.scheduler_locks.items.append(
            {
                "_id": app_scheduler.status()["lock_id"],
                "owner_id": "scheduler-test-node",
                "expires_at": naive_expires_at,
                "heartbeat_at": naive_heartbeat_at,
            }
        )

        response = client.get("/api/v1/admin/system/health", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["scheduler_lock"]["owner_id"] == "scheduler-test-node"
        assert body["scheduler_lock"]["is_stale"] is True
        assert body["scheduler_lock"]["expires_at"].endswith(("Z", "+00:00"))
        assert body["scheduler_lock"]["heartbeat_at"].endswith(("Z", "+00:00"))
    finally:
        app_scheduler._enabled, app_scheduler._running, app_scheduler._is_leader = original_scheduler_state
        observability_state.reset()


def test_clubs_observability_history_normalizes_naive_snapshot_datetimes() -> None:
    fake_db = _setup_fake_db()
    naive_recorded_at = (datetime.now(timezone.utc) - timedelta(minutes=10)).replace(tzinfo=None)
    fake_db.system_health_snapshots.items.append(
        {
            "_id": ObjectId(),
            "bucket_minute": "2026-04-07T09:00:00+00:00",
            "recorded_at": naive_recorded_at,
            "club_requests_15m": 4,
            "club_p95_duration_ms_15m": 1800,
            "club_slow_requests_15m": 1,
            "club_server_errors_15m": 0,
        }
    )

    history = asyncio.run(snapshot_service.get_clubs_observability_history(database=fake_db))

    assert history["summary"]["hourly_windows_24h"] >= 1
    assert history["hourly_24h"][0]["club_requests_peak"] == 4


def test_system_health_snapshot_pruning_keeps_store_bounded() -> None:
    fake_db = _setup_fake_db()
    original_retention = snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES
    original_last_pruned_bucket = snapshot_service._last_pruned_bucket
    original_last_pruned_at = snapshot_service._last_pruned_at
    original_last_pruned_deleted_count = snapshot_service._last_pruned_deleted_count
    try:
        snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES = 2
        snapshot_service._last_pruned_bucket = None
        snapshot_service._last_pruned_at = None
        snapshot_service._last_pruned_deleted_count = 0
        base_time = datetime(2026, 3, 12, 12, 0, tzinfo=timezone.utc)

        for minute_offset in range(4):
            timestamp = base_time + timedelta(minutes=minute_offset)
            asyncio.run(
                snapshot_service.persist_system_health_snapshot(
                    payload={
                        "timestamp": timestamp,
                        "db_status": "ok",
                        "alert_count": 0,
                        "observability": {
                            "request_metrics": {
                                "requests_15m": minute_offset + 1,
                                "server_error_rate_pct_15m": 0.0,
                                "p95_duration_ms_15m": 100,
                            },
                            "ai_metrics": {
                                "queued_jobs": minute_offset,
                                "running_jobs": 0,
                                "failed_jobs": 0,
                                "oldest_queued_age_seconds": minute_offset * 10,
                                "fallback_rate_pct_15m": 0.0,
                                "last_similarity_candidate_count": minute_offset * 5,
                            },
                        },
                    },
                    database=fake_db,
                )
            )

        buckets = sorted(item["bucket_minute"] for item in fake_db.system_health_snapshots.items)
        assert len(buckets) == 3
        assert buckets == [
            "2026-03-12T12:01:00+00:00",
            "2026-03-12T12:02:00+00:00",
            "2026-03-12T12:03:00+00:00",
        ]
        status = asyncio.run(snapshot_service.get_system_health_snapshot_store_status(database=fake_db))
        assert status["retained_rows"] == 3
        assert status["max_retained_rows"] == 3
        assert status["is_within_retention_bound"] is True
        assert status["last_pruned_deleted_count"] == 1
        latest_snapshot = max(fake_db.system_health_snapshots.items, key=lambda item: item["bucket_minute"])
        assert latest_snapshot["retained_rows"] == 3
        assert latest_snapshot["last_pruned_deleted_count"] == 1
        assert latest_snapshot["is_within_retention_bound"] is True
    finally:
        snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES = original_retention
        snapshot_service._last_pruned_bucket = original_last_pruned_bucket
        snapshot_service._last_pruned_at = original_last_pruned_at
        snapshot_service._last_pruned_deleted_count = original_last_pruned_deleted_count


def test_system_health_snapshot_builds_long_horizon_club_observability() -> None:
    fake_db = _setup_fake_db()
    original_retention = snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES
    original_retention_days = snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS
    original_last_pruned_bucket = snapshot_service._last_pruned_bucket
    original_last_pruned_at = snapshot_service._last_pruned_at
    original_last_pruned_deleted_count = snapshot_service._last_pruned_deleted_count
    try:
        snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS = 14
        snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES = 14 * 24 * 60
        snapshot_service._last_pruned_bucket = None
        snapshot_service._last_pruned_at = None
        snapshot_service._last_pruned_deleted_count = 0
        base_time = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0) - timedelta(days=6)

        for day_offset in range(7):
            for hour_offset in (0, 8, 16):
                timestamp = base_time + timedelta(days=day_offset, hours=hour_offset)
                requests = 8 + day_offset if day_offset >= 4 else 2 + day_offset
                p95 = 2400 if day_offset >= 5 else 700
                slow = 4 if day_offset >= 5 else 0
                errors = 1 if day_offset == 6 and hour_offset == 16 else 0
                asyncio.run(
                    snapshot_service.persist_system_health_snapshot(
                        payload={
                            "timestamp": timestamp,
                            "db_status": "ok",
                            "alert_count": 0,
                            "observability": {
                                "request_metrics": {
                                    "requests_15m": requests + 3,
                                    "server_error_rate_pct_15m": 0.0,
                                    "p95_duration_ms_15m": 400,
                                },
                                "clubs_metrics": {
                                    "requests_15m": requests,
                                    "slow_requests_15m": slow,
                                    "server_errors_15m": errors,
                                    "p95_duration_ms_15m": p95,
                                },
                                "ai_metrics": {
                                    "queued_jobs": 0,
                                    "running_jobs": 0,
                                    "failed_jobs": 0,
                                    "oldest_queued_age_seconds": 0,
                                    "fallback_rate_pct_15m": 0.0,
                                    "last_similarity_candidate_count": 0,
                                },
                            },
                        },
                        database=fake_db,
                    )
                )

        history = asyncio.run(snapshot_service.get_clubs_observability_history(database=fake_db))
        assert history["summary"]["retention_days"] == 14
        assert len(history["hourly_24h"]) >= 1
        assert len(history["daily_14d"]) >= 7
        assert history["summary"]["pressure_days_14d"] >= 1
        assert history["summary"]["latest_pressure_level"] in {"warning", "critical"}
        assert any(point["pressure_level"] in {"warning", "critical"} for point in history["daily_14d"])
        assert history["recent_pressure_windows"]
    finally:
        snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_MINUTES = original_retention
        snapshot_service.SYSTEM_HEALTH_SNAPSHOT_RETENTION_DAYS = original_retention_days
        snapshot_service._last_pruned_bucket = original_last_pruned_bucket
        snapshot_service._last_pruned_at = original_last_pruned_at
        snapshot_service._last_pruned_deleted_count = original_last_pruned_deleted_count


def test_admin_analytics_bootstrap_uses_snapshot_after_first_live_compute() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_analytics_snapshot@example.com")
    now = datetime.now(timezone.utc)

    fake_db.users.items.extend(
        [
            {"_id": ObjectId(), "email": "alpha@example.com"},
            {"_id": ObjectId(), "email": "beta@example.com"},
        ]
    )
    fake_db.students.items.append({"_id": ObjectId(), "email": "student@example.com", "is_active": True})
    fake_db.clubs.items.append({"_id": ObjectId(), "status": "active"})
    fake_db.club_members.items.append({"_id": ObjectId(), "status": "active"})
    fake_db.club_events.items.append({"_id": ObjectId(), "event_date": now + timedelta(days=2)})
    fake_db.event_registrations.items.append({"_id": ObjectId(), "status": "registered"})
    fake_db.assignments.items.extend([{"_id": ObjectId()}, {"_id": ObjectId()}])
    fake_db.submissions.items.append({"_id": ObjectId()})
    fake_db.review_tickets.items.extend(
        [
            {"_id": ObjectId(), "status": "pending"},
            {
                "_id": ObjectId(),
                "status": "resolved",
                "created_at": now - timedelta(hours=3),
                "resolved_at": now - timedelta(hours=1),
            },
        ]
    )
    fake_db.audit_logs.items.extend(
        [
            {
                "_id": ObjectId(),
                "action_type": "login",
                "actor_user_id": "user-1",
                "created_at": now - timedelta(hours=2),
            },
            {
                "_id": ObjectId(),
                "action_type": "login",
                "actor_user_id": "user-2",
                "created_at": now - timedelta(hours=1),
            },
            {
                "_id": ObjectId(),
                "action": "error",
                "severity": "high",
                "created_at": now - timedelta(minutes=30),
            },
        ]
    )

    response = client.get("/api/v1/admin/analytics/bootstrap", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert body["snapshot_served_from"] == "live"
    assert body["snapshot_age_hours"] == 0
    assert body["overview"]["total_users"] == 3
    assert body["overview"]["active_students"] == 1
    assert body["overview"]["active_clubs"] == 1
    assert body["overview"]["assignments_total"] == 2
    assert body["overview"]["submissions_total"] == 1
    assert body["overview"]["pending_review_tickets"] == 1
    assert body["overview"]["events_this_week"] == 1
    assert body["overview"]["system_errors_24h"] == 1
    assert body["metrics"]["daily_active_users"] >= 2
    assert body["metrics"]["login_count_24h"] >= 2
    assert body["metrics"]["assignment_completion_pct"] == 50.0
    assert body["metrics"]["club_participation_pct"] == 100.0
    assert body["metrics"]["event_attendance_pct"] == 100.0
    assert body["metrics"]["review_ticket_sla_hours"] == 2.0
    assert len(fake_db.analytics_snapshots.items) == 1

    second = client.get("/api/v1/admin/analytics/bootstrap", headers=headers)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["snapshot_served_from"] == "snapshot"
    assert second_body["snapshot_age_hours"] >= 0
    assert second_body["overview"]["total_users"] == 3
    assert second_body["metrics"]["assignment_completion_pct"] == 50.0
    assert len(fake_db.analytics_snapshots.items) == 1

    refreshed = client.get("/api/v1/admin/analytics/bootstrap?refresh=true", headers=headers)
    assert refreshed.status_code == 200
    refreshed_body = refreshed.json()
    assert refreshed_body["snapshot_served_from"] == "live"
    assert refreshed_body["snapshot_age_hours"] == 0
    assert len(fake_db.analytics_snapshots.items) == 1


def test_admin_dashboard_and_summary_use_persisted_analytics_snapshot() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_dashboard_snapshot@example.com")
    now = datetime.now(timezone.utc)

    fake_db.users.items.extend(
        [
            {"_id": ObjectId(), "email": "alpha@example.com"},
            {"_id": ObjectId(), "email": "beta@example.com"},
        ]
    )
    fake_db.students.items.extend(
        [
            {"_id": ObjectId(), "email": "student1@example.com", "is_active": True},
            {"_id": ObjectId(), "email": "student2@example.com", "is_active": False},
        ]
    )
    fake_db.programs.items.append({"_id": ObjectId(), "name": "Program One"})
    fake_db.batches.items.append({"_id": ObjectId(), "name": "Batch One"})
    fake_db.semesters.items.append({"_id": ObjectId(), "label": "Semester 1"})
    fake_db.classes.items.append({"_id": ObjectId(), "name": "Section A"})
    fake_db.subjects.items.append({"_id": ObjectId(), "name": "Algorithms"})
    fake_db.assignments.items.extend([{"_id": ObjectId()}, {"_id": ObjectId()}])
    fake_db.submissions.items.append({"_id": ObjectId()})
    fake_db.evaluations.items.append({"_id": ObjectId()})
    fake_db.similarity_logs.items.append({"_id": ObjectId(), "is_flagged": True})
    fake_db.notices.items.append(
        {
            "_id": ObjectId(),
            "title": "Urgent Notice",
            "priority": "urgent",
            "is_active": True,
            "created_at": now - timedelta(minutes=5),
            "scheduled_at": now - timedelta(minutes=10),
            "author_user_id": None,
            "target_roles": ["admin"],
            "read_by": [],
        }
    )
    fake_db.clubs.items.append({"_id": ObjectId(), "status": "active"})
    fake_db.club_members.items.append({"_id": ObjectId(), "status": "active"})
    fake_db.club_events.items.append({"_id": ObjectId(), "event_date": now + timedelta(days=2)})
    fake_db.event_registrations.items.append({"_id": ObjectId(), "status": "registered"})
    fake_db.review_tickets.items.append({"_id": ObjectId(), "status": "pending"})
    fake_db.audit_logs.items.append(
        {
            "_id": ObjectId(),
            "action_type": "login",
            "actor_user_id": "user-1",
            "created_at": now - timedelta(hours=1),
        }
    )

    first_dashboard = client.get("/api/v1/analytics/dashboard", headers=headers)
    assert first_dashboard.status_code == 200, first_dashboard.text
    first_body = first_dashboard.json()
    assert first_body["snapshot_served_from"] == "live"
    assert first_body["summary"]["users"] == 3
    assert first_body["summary"]["students"] == 2
    assert first_body["summary"]["programs"] == 1
    assert first_body["summary"]["assignments"] == 2
    assert first_body["summary"]["similarity_flags"] == 1
    assert len(first_body["urgent_notices"]) == 1
    assert len(fake_db.analytics_snapshots.items) == 1

    second_dashboard = client.get("/api/v1/analytics/dashboard", headers=headers)
    assert second_dashboard.status_code == 200
    second_body = second_dashboard.json()
    assert second_body["snapshot_served_from"] == "snapshot"
    assert second_body["summary"]["users"] == 3
    assert second_body["summary"]["students"] == 2
    assert len(fake_db.analytics_snapshots.items) == 1

    summary = client.get("/api/v1/analytics/summary", headers=headers)
    assert summary.status_code == 200, summary.text
    summary_body = summary.json()
    assert summary_body["snapshot_served_from"] == "snapshot"
    assert summary_body["summary"]["users"] == 3
    assert summary_body["summary"]["students"] == 2
    assert summary_body["summary"]["classes"] == 1
    assert summary_body["summary"]["club_events"] == 1


def test_section_read_model_materializes_and_refreshes_after_semester_and_coordinator_updates() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_section_read_model@example.com")

    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator Teacher",
            "email": "coordinator_section_read_model@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201
    teacher_id = teacher.json()["id"]

    structure = _seed_canonical_structure(fake_db, suffix="SRM1", semester_number=3)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="Section Read Model",
            class_coordinator_user_id=teacher_id,
        ),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text
    section_body = section.json()
    section_detail = client.get(f"/api/v1/sections/{section_body['id']}", headers=admin_headers)
    assert section_detail.status_code == 200, section_detail.text
    section_body = section_detail.json()
    assert section_body["program_name"] == "Program SRM1"
    assert section_body["semester_label"] == "Semester 3"
    assert section_body["class_coordinator_name"] == "Coordinator Teacher"
    assert len(fake_db.section_read_models.items) == 1

    read_model = fake_db.section_read_models.items[0]
    assert str(read_model["_id"]) == section_body["id"]
    assert read_model["section_id"] == section_body["id"]
    assert read_model["program_name"] == "Program SRM1"
    assert read_model["semester_label"] == "Semester 3"
    assert read_model["class_coordinator_name"] == "Coordinator Teacher"

    semester_update = client.put(
        f"/api/v1/semesters/{structure['semester_id']}",
        json={"label": "Semester III - Updated"},
        headers=admin_headers,
    )
    assert semester_update.status_code == 200, semester_update.text

    after_semester = client.get(f"/api/v1/sections/{section_body['id']}", headers=admin_headers)
    assert after_semester.status_code == 200
    assert after_semester.json()["semester_label"] == "Semester III - Updated"
    assert fake_db.section_read_models.items[0]["semester_label"] == "Semester III - Updated"

    deactivated = client.delete(f"/api/v1/users/{teacher_id}", headers=admin_headers)
    assert deactivated.status_code == 200, deactivated.text

    after_deactivate = client.get(f"/api/v1/sections/{section_body['id']}", headers=admin_headers)
    assert after_deactivate.status_code == 200
    assert after_deactivate.json()["class_coordinator_user_id"] is None
    assert after_deactivate.json()["class_coordinator_name"] is None
    assert fake_db.section_read_models.items[0]["class_coordinator_user_id"] is None
    assert fake_db.section_read_models.items[0]["class_coordinator_name"] is None


def test_batch_and_semester_read_models_refresh_after_program_and_batch_updates() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_batch_semester_read_model@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="BRM2", duration_years=4, semester_number=1)
    batch = client.post(
        "/api/v1/batches/",
        json={
            "program_id": structure["program_id"],
            "name": "Batch BRM2 Custom",
            "code": "BRM2-CUSTOM",
            "start_year": 2025,
            "end_year": 2029,
        },
        headers=admin_headers,
    )
    assert batch.status_code == 201, batch.text
    batch_body = batch.json()
    assert batch_body["program_name"] == "Program BRM2"
    assert batch_body["program_duration_years"] == 4
    assert len(fake_db.batch_read_models.items) == 1

    semesters = client.get(f"/api/v1/semesters/?batch_id={batch_body['id']}", headers=admin_headers)
    assert semesters.status_code == 200, semesters.text
    semester_items = semesters.json()
    assert len(semester_items) == 8
    assert semester_items[0]["batch_name"] == "Batch BRM2 Custom"
    assert semester_items[0]["program_name"] == "Program BRM2"
    semester_id = semester_items[0]["id"]
    assert len(fake_db.semester_read_models.items) == 8

    program_update = client.put(
        f"/api/v1/programs/{structure['program_id']}",
        json={"name": "Program BRM2 Updated"},
        headers=admin_headers,
    )
    assert program_update.status_code == 200, program_update.text

    batch_after_program = client.get(f"/api/v1/batches/{batch_body['id']}", headers=admin_headers)
    assert batch_after_program.status_code == 200
    assert batch_after_program.json()["program_name"] == "Program BRM2 Updated"

    semester_after_program = client.get(f"/api/v1/semesters/{semester_id}", headers=admin_headers)
    assert semester_after_program.status_code == 200
    assert semester_after_program.json()["program_name"] == "Program BRM2 Updated"

    batch_update = client.put(
        f"/api/v1/batches/{batch_body['id']}",
        json={"name": "Batch BRM2 Custom Updated"},
        headers=admin_headers,
    )
    assert batch_update.status_code == 200, batch_update.text
    assert batch_update.json()["program_name"] == "Program BRM2 Updated"

    semester_after_batch = client.get(f"/api/v1/semesters/{semester_id}", headers=admin_headers)
    assert semester_after_batch.status_code == 200
    assert semester_after_batch.json()["batch_name"] == "Batch BRM2 Custom Updated"
    assert fake_db.batch_read_models.items[0]["program_name"] == "Program BRM2 Updated"
    assert any(item["batch_name"] == "Batch BRM2 Custom Updated" for item in fake_db.semester_read_models.items)


def test_course_offering_and_class_slot_read_models_refresh_after_subject_section_and_group_updates() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_read_model@example.com")

    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Delivery Teacher",
            "email": "delivery_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201
    teacher_id = teacher.json()["id"]

    structure = _seed_canonical_structure(fake_db, suffix="DLV1", semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Delivery Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text
    section_id = section.json()["id"]

    group = client.post(
        "/api/v1/groups/",
        json={
            "section_id": section_id,
            "name": "Group Alpha",
            "code": "GA",
            "description": "Alpha group",
        },
        headers=admin_headers,
    )
    assert group.status_code == 201, group.text
    group_id = group.json()["id"]

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Distributed Systems", "code": "DS-DLV1", "description": "DS"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text
    subject_id = subject.json()["id"]

    offering = client.post(
        "/api/v1/course-offerings/",
        json={
            "subject_id": subject_id,
            "teacher_user_id": teacher_id,
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "section_id": section_id,
            "group_id": group_id,
            "academic_year": "2025-26",
            "offering_type": "theory",
        },
        headers=admin_headers,
    )
    assert offering.status_code == 201, offering.text
    offering_id = offering.json()["id"]

    slot = client.post(
        "/api/v1/class-slots/",
        json={
            "course_offering_id": offering_id,
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:00",
            "room_code": "LAB-1",
        },
        headers=admin_headers,
    )
    assert slot.status_code == 201, slot.text

    offerings_before = client.get(f"/api/v1/course-offerings/?section_id={section_id}", headers=admin_headers)
    assert offerings_before.status_code == 200, offerings_before.text
    assert offerings_before.json()[0]["subject_name"] == "Distributed Systems"
    assert offerings_before.json()[0]["section_name"] == "Delivery Section"
    assert offerings_before.json()[0]["group_name"] == "Group Alpha"

    slots_before = client.get(f"/api/v1/class-slots/?section_id={section_id}", headers=admin_headers)
    assert slots_before.status_code == 200, slots_before.text
    assert slots_before.json()[0]["subject_name"] == "Distributed Systems"
    assert slots_before.json()[0]["section_name"] == "Delivery Section"
    assert slots_before.json()[0]["group_name"] == "Group Alpha"
    assert slots_before.json()[0]["semester_label"] == "Semester 2"

    update_subject = client.put(
        f"/api/v1/subjects/{subject_id}",
        json={"name": "Distributed Systems Updated"},
        headers=admin_headers,
    )
    assert update_subject.status_code == 200, update_subject.text

    update_section = client.put(
        f"/api/v1/sections/{section_id}",
        json={"name": "Delivery Section Updated"},
        headers=admin_headers,
    )
    assert update_section.status_code == 200, update_section.text

    update_group = client.put(
        f"/api/v1/groups/{group_id}",
        json={"name": "Group Alpha Updated"},
        headers=admin_headers,
    )
    assert update_group.status_code == 200, update_group.text

    offerings_after = client.get(f"/api/v1/course-offerings/?section_id={section_id}", headers=admin_headers)
    assert offerings_after.status_code == 200
    assert offerings_after.json()[0]["subject_name"] == "Distributed Systems Updated"
    assert offerings_after.json()[0]["section_name"] == "Delivery Section Updated"
    assert offerings_after.json()[0]["group_name"] == "Group Alpha Updated"

    slots_after = client.get(f"/api/v1/class-slots/?section_id={section_id}", headers=admin_headers)
    assert slots_after.status_code == 200
    assert slots_after.json()[0]["subject_name"] == "Distributed Systems Updated"
    assert slots_after.json()[0]["section_name"] == "Delivery Section Updated"
    assert slots_after.json()[0]["group_name"] == "Group Alpha Updated"
    assert len(fake_db.course_offering_read_models.items) == 1
    assert len(fake_db.class_slot_read_models.items) == 1

