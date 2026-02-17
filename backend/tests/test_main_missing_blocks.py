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

    section = client.post(
        "/api/v1/sections/",
        json={"name": "A", "program": "BCA", "academic_year": "2026-27", "semester": 2},
        headers=admin_headers,
    )
    assert section.status_code == 201

    course = client.post(
        "/api/v1/courses/",
        json={"name": "BCA", "code": "BCA-SIM", "description": "desc"},
        headers=admin_headers,
    )
    year = client.post(
        "/api/v1/years/",
        json={"course_id": course.json()["id"], "year_number": 1, "label": "FY"},
        headers=admin_headers,
    )
    class_item = client.post(
        "/api/v1/classes/",
        json={
            "course_id": course.json()["id"],
            "year_id": year.json()["id"],
            "name": "BCA FY",
            "section": "A",
            "class_coordinator_user_id": coordinator_teacher.json()["id"],
        },
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
            "section_id": section.json()["id"],
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
