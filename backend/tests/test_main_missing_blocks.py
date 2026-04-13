import asyncio
from datetime import datetime, timedelta, timezone

from bson import ObjectId
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.observability import observability_state
from app.api.v1.endpoints import similarity as similarity_endpoint
from app.main import app
from app.api.v1.endpoints import attendance_records as attendance_records_endpoint
from app.api.v1.endpoints import submissions as submissions_endpoint
from app.services.ai_chat_service import generate_evaluation_chat_reply
from app.services.ai_jobs import process_ai_jobs_once
from app.services.file_parser import ParsedFileResult
from app.services.fairness_regression import run_fairness_regression_suite
from app.services.reviewer_outcome_calibration import build_reviewer_outcome_calibration_report
from app.services.semantic_shadow_calibration import run_semantic_shadow_calibration
from app.services.similarity_engine import prefilter_similarity_candidates
from app.services import ai_jobs as ai_jobs_service
from app.services import background_jobs as background_jobs_service
from app.services import communication_digests as communication_digests_service
from app.services import communication_delivery_retry as communication_delivery_retry_service
from app.services import notifications as notifications_service
from app.services.academic_students import list_students_for_section, resolve_student_academic_context_for_user
from app.services.scheduler import app_scheduler
from app.services import system_health_snapshots as snapshot_service
from tests.test_auth import FakeUsersCollection, _create_section_payload, _seed_canonical_structure, _setup_fake_db


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


def _teacher_headers(client: TestClient, email: str) -> dict:
    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher User",
            "email": email,
            "password": "password123",
            "role": "teacher",
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


def test_evaluation_release_sets_result_metadata_and_admin_score_change_unreleases() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin_headers = _admin_headers(client, "admin_eval_release@example.com")
    teacher_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher Release",
            "email": "teacher_eval_release@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher_register.status_code == 201
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_eval_release@example.com", "password": "password123"},
    )
    assert teacher_login.status_code == 200
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Release Flow", "description": "Desc", "total_marks": 100},
        headers=teacher_headers,
    )
    assert assignment.status_code == 201
    student_headers = _student_headers(client, "student_eval_release@example.com")
    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("report.txt", b"evaluation release content", "text/plain")},
        headers=student_headers,
    )
    assert upload.status_code == 201

    created = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": upload.json()["id"],
            "attendance_percent": 88,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 15,
            "final_exam": 48,
            "is_finalized": False,
        },
        headers=teacher_headers,
    )
    assert created.status_code == 201
    evaluation_id = created.json()["id"]
    assert created.json()["result_status"] == "draft"

    finalized = client.patch(f"/api/v1/evaluations/{evaluation_id}/finalize", headers=teacher_headers)
    assert finalized.status_code == 200
    assert finalized.json()["result_status"] == "finalized_unreleased"

    released = client.patch(f"/api/v1/evaluations/{evaluation_id}/release", headers=teacher_headers)
    assert released.status_code == 200, released.text
    released_body = released.json()
    assert released_body["result_status"] == "released"
    assert released_body["released_at"] is not None
    assert released_body["released_by_user_id"] == teacher_register.json()["id"]
    assert released_body["result_version"] == 2

    admin_update = client.put(
        f"/api/v1/evaluations/{evaluation_id}",
        json={"final_exam": 49, "remarks": "Adjusted after audit review"},
        headers=admin_headers,
    )
    assert admin_update.status_code == 200, admin_update.text
    updated_body = admin_update.json()
    assert updated_body["is_finalized"] is True
    assert updated_body["result_status"] == "finalized_unreleased"
    assert updated_body["released_at"] is None
    assert updated_body["released_by_user_id"] is None
    assert updated_body["final_exam"] == 49
    assert updated_body["grand_total"] == 79.0


def test_student_official_marksheet_only_includes_released_results() -> None:
    fake_db = _setup_fake_db()
    fake_db.attendance_records = FakeUsersCollection()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_marksheet@example.com")

    teacher_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher Marksheet",
            "email": "teacher_marksheet@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher_register.status_code == 201
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_marksheet@example.com", "password": "password123"},
    )
    assert teacher_login.status_code == 200
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Marksheet",
            "email": "student_marksheet@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_register.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_marksheet@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    existing_student = next(
        (
            item
            for item in fake_db.students.items
            if item.get("user_id") == student_register.json()["id"] or item.get("email") == "student_marksheet@example.com"
        ),
        None,
    )
    if existing_student is not None:
        existing_student.update(
            {
                "full_name": "Student Marksheet",
                "roll_number": "MRK-001",
                "email": "student_marksheet@example.com",
                "user_id": student_register.json()["id"],
                "is_active": True,
            }
        )
    else:
        student_profile = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Student Marksheet",
                "roll_number": "MRK-001",
                "email": "student_marksheet@example.com",
                "user_id": student_register.json()["id"],
            },
            headers=admin_headers,
        )
        assert student_profile.status_code == 201, student_profile.text

    assignment_a = client.post(
        "/api/v1/assignments/",
        json={"title": "Released Assignment", "description": "Desc", "total_marks": 100},
        headers=teacher_headers,
    )
    assert assignment_a.status_code == 201
    assignment_b = client.post(
        "/api/v1/assignments/",
        json={"title": "Draft Assignment", "description": "Desc", "total_marks": 100},
        headers=teacher_headers,
    )
    assert assignment_b.status_code == 201

    submission_a = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_a.json()["id"]},
        files={"file": ("released.txt", b"released marksheet content", "text/plain")},
        headers=student_headers,
    )
    assert submission_a.status_code == 201
    submission_b = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_b.json()["id"]},
        files={"file": ("draft.txt", b"draft marksheet content", "text/plain")},
        headers=student_headers,
    )
    assert submission_b.status_code == 201

    released_eval = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission_a.json()["id"],
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
    assert released_eval.status_code == 201
    finalize_released = client.patch(f"/api/v1/evaluations/{released_eval.json()['id']}/finalize", headers=teacher_headers)
    assert finalize_released.status_code == 200
    publish_released = client.patch(f"/api/v1/evaluations/{released_eval.json()['id']}/release", headers=teacher_headers)
    assert publish_released.status_code == 200

    unreleased_eval = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission_b.json()["id"],
            "attendance_percent": 86,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 7,
            "viva": 14,
            "final_exam": 45,
            "is_finalized": True,
        },
        headers=teacher_headers,
    )
    assert unreleased_eval.status_code == 201
    assert unreleased_eval.json()["result_status"] == "finalized_unreleased"

    marksheet = client.get("/api/v1/evaluations/results/marksheet", headers=student_headers)
    assert marksheet.status_code == 200, marksheet.text
    body = marksheet.json()
    assert body["student_user_id"] == student_register.json()["id"]
    assert body["roll_number"] == "MRK-001"
    assert body["released_results_count"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["submission_id"] == submission_a.json()["id"]
    assert body["items"][0]["submission_label"] == "Released Assignment"
    assert body["items"][0]["result_version"] == 2


def test_admin_official_marksheet_can_target_student_by_user_id() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_marksheet_target@example.com")

    teacher_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher Target",
            "email": "teacher_marksheet_target@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher_register.status_code == 201
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_marksheet_target@example.com", "password": "password123"},
    )
    assert teacher_login.status_code == 200
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Target",
            "email": "student_marksheet_target@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_register.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_marksheet_target@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    existing_student = next(
        (
            item
            for item in fake_db.students.items
            if item.get("user_id") == student_register.json()["id"] or item.get("email") == "student_marksheet_target@example.com"
        ),
        None,
    )
    if existing_student is not None:
        existing_student.update(
            {
                "full_name": "Student Target",
                "roll_number": "MRK-ADM-001",
                "email": "student_marksheet_target@example.com",
                "user_id": student_register.json()["id"],
                "is_active": True,
            }
        )
    else:
        student_profile = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Student Target",
                "roll_number": "MRK-ADM-001",
                "email": "student_marksheet_target@example.com",
                "user_id": student_register.json()["id"],
            },
            headers=admin_headers,
        )
        assert student_profile.status_code == 201, student_profile.text

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Admin Release Assignment", "description": "Desc", "total_marks": 100},
        headers=teacher_headers,
    )
    assert assignment.status_code == 201

    submission = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("released-admin.txt", b"admin marksheet content", "text/plain")},
        headers=student_headers,
    )
    assert submission.status_code == 201

    released_eval = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission.json()["id"],
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 15,
            "final_exam": 51,
            "is_finalized": False,
        },
        headers=teacher_headers,
    )
    assert released_eval.status_code == 201
    finalize_released = client.patch(f"/api/v1/evaluations/{released_eval.json()['id']}/finalize", headers=teacher_headers)
    assert finalize_released.status_code == 200
    publish_released = client.patch(f"/api/v1/evaluations/{released_eval.json()['id']}/release", headers=teacher_headers)
    assert publish_released.status_code == 200

    marksheet = client.get(
        f"/api/v1/evaluations/results/marksheet?student_user_id={student_register.json()['id']}",
        headers=admin_headers,
    )
    assert marksheet.status_code == 200, marksheet.text
    body = marksheet.json()
    assert body["student_user_id"] == student_register.json()["id"]
    assert body["student_name"] == "Student Target"
    assert body["roll_number"] == "MRK-ADM-001"
    assert body["released_results_count"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["submission_label"] == "Admin Release Assignment"


def test_student_academic_context_uses_enrollment_as_canonical_section() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_canonical_slots@example.com")

    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Canonical Teacher",
            "email": "canonical_slots_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Canonical Student",
            "email": "canonical_slots_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "canonical_slots_student@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    structure = _seed_canonical_structure(fake_db, suffix="CNS1", semester_number=2)
    stale_section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Legacy Section"),
        headers=admin_headers,
    )
    assert stale_section.status_code == 201, stale_section.text
    canonical_section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Canonical Section"),
        headers=admin_headers,
    )
    assert canonical_section.status_code == 201, canonical_section.text

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Operating Systems", "code": "OS-CNS1", "description": "OS"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text

    offering = client.post(
        "/api/v1/course-offerings/",
        json={
            "subject_id": subject.json()["id"],
            "teacher_user_id": teacher.json()["id"],
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "section_id": canonical_section.json()["id"],
            "group_id": None,
            "academic_year": "2025-26",
            "offering_type": "theory",
        },
        headers=admin_headers,
    )
    assert offering.status_code == 201, offering.text

    slot = client.post(
        "/api/v1/class-slots/",
        json={
            "course_offering_id": offering.json()["id"],
            "day": "Tuesday",
            "start_time": "10:00",
            "end_time": "11:00",
            "room_code": "B-201",
        },
        headers=admin_headers,
    )
    assert slot.status_code == 201, slot.text

    existing_student = next(
        (
            item
            for item in fake_db.students.items
            if item.get("user_id") == student.json()["id"] or item.get("email") == "canonical_slots_student@example.com"
        ),
        None,
    )
    if existing_student is not None:
        existing_student.update(
            {
                "full_name": "Canonical Student",
                "roll_number": "CNS1-001",
                "email": "canonical_slots_student@example.com",
                "user_id": student.json()["id"],
                "class_id": stale_section.json()["id"],
                "group_id": None,
                "is_active": True,
            }
        )
        student_doc_id = str(existing_student["_id"])
    else:
        student_profile = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Canonical Student",
                "roll_number": "CNS1-001",
                "email": "canonical_slots_student@example.com",
                "user_id": student.json()["id"],
                "class_id": stale_section.json()["id"],
                "group_id": None,
            },
            headers=admin_headers,
        )
        assert student_profile.status_code == 201, student_profile.text
        student_doc_id = student_profile.json()["id"]

    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": canonical_section.json()["id"], "student_id": student_doc_id},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    student_user = next(item for item in fake_db.users.items if item.get("email") == "canonical_slots_student@example.com")
    student_context = asyncio.run(resolve_student_academic_context_for_user(student_user, database=fake_db))
    assert student_context is not None
    assert student_context["canonical_class_id"] == canonical_section.json()["id"]

    section_students = asyncio.run(
        list_students_for_section(canonical_section.json()["id"], database=fake_db)
    )
    assert len(section_students) == 1
    assert str(section_students[0]["_id"]) == student_doc_id

    listed_students = client.get("/api/v1/students/", headers=admin_headers)
    assert listed_students.status_code == 200, listed_students.text
    listed_body = listed_students.json()
    target_student = next(item for item in listed_body if item["id"] == student_doc_id)
    assert target_student["canonical_class_id"] == canonical_section.json()["id"]
    assert target_student["placement_source"] == "enrollment"


def test_attendance_summary_exposes_percentages_and_shortage_flags() -> None:
    fake_db = _setup_fake_db()
    fake_db.attendance_records = FakeUsersCollection()
    attendance_records_endpoint.db = fake_db
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_attendance_summary@example.com")

    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Summary Teacher",
            "email": "attendance_summary_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Summary Student",
            "email": "attendance_summary_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "attendance_summary_student@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    structure = _seed_canonical_structure(fake_db, suffix="ATS1", semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Summary Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Distributed Systems", "code": "DS-ATS1", "description": "DS"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text

    offering = client.post(
        "/api/v1/course-offerings/",
        json={
            "subject_id": subject.json()["id"],
            "teacher_user_id": teacher.json()["id"],
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "section_id": section.json()["id"],
            "group_id": None,
            "academic_year": "2025-26",
            "offering_type": "theory",
        },
        headers=admin_headers,
    )
    assert offering.status_code == 201, offering.text

    slot_one = client.post(
        "/api/v1/class-slots/",
        json={
            "course_offering_id": offering.json()["id"],
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:00",
            "room_code": "A-101",
        },
        headers=admin_headers,
    )
    assert slot_one.status_code == 201, slot_one.text
    slot_two = client.post(
        "/api/v1/class-slots/",
        json={
            "course_offering_id": offering.json()["id"],
            "day": "Wednesday",
            "start_time": "09:00",
            "end_time": "10:00",
            "room_code": "A-101",
        },
        headers=admin_headers,
    )
    assert slot_two.status_code == 201, slot_two.text
    slot_one_id = str(fake_db.class_slots.items[-2]["_id"])
    slot_two_id = str(fake_db.class_slots.items[-1]["_id"])

    existing_student = next(
        (
            item
            for item in fake_db.students.items
            if item.get("user_id") == student.json()["id"] or item.get("email") == "attendance_summary_student@example.com"
        ),
        None,
    )
    if existing_student is not None:
        existing_student.update(
            {
                "full_name": "Summary Student",
                "roll_number": "ATS1-001",
                "email": "attendance_summary_student@example.com",
                "user_id": student.json()["id"],
                "class_id": section.json()["id"],
                "is_active": True,
            }
        )
        student_doc_id = str(existing_student["_id"])
    else:
        student_profile = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Summary Student",
                "roll_number": "ATS1-001",
                "email": "attendance_summary_student@example.com",
                "user_id": student.json()["id"],
                "class_id": section.json()["id"],
            },
            headers=admin_headers,
        )
        assert student_profile.status_code == 201, student_profile.text
        student_doc_id = student_profile.json()["id"]

    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section.json()["id"], "student_id": student_doc_id},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    fake_db.attendance_records.items.extend(
        [
            {
                "_id": ObjectId(),
                "class_slot_id": slot_one_id,
                "student_id": student_doc_id,
                "status": "present",
                "marked_by_user_id": admin_headers["Authorization"],
                "marked_at": datetime.now(timezone.utc),
                "is_active": True,
            },
            {
                "_id": ObjectId(),
                "class_slot_id": slot_two_id,
                "student_id": student_doc_id,
                "status": "absent",
                "marked_by_user_id": admin_headers["Authorization"],
                "marked_at": datetime.now(timezone.utc),
                "is_active": True,
            },
        ]
    )

    summary = client.get(
        f"/api/v1/attendance-records/summary?section_id={section.json()['id']}&shortage_threshold=75",
        headers=admin_headers,
    )
    assert summary.status_code == 200, summary.text
    summary_body = summary.json()
    assert summary_body["total_students"] == 1
    assert summary_body["total_slots"] == 2
    assert summary_body["average_attendance_percent"] == 50.0
    assert summary_body["shortage_risk_count"] == 1
    assert summary_body["students"][0]["attendance_percent"] == 50.0
    assert summary_body["students"][0]["shortage_risk"] is True

    my_summary = client.get("/api/v1/attendance-records/my-summary?shortage_threshold=75", headers=student_headers)
    assert my_summary.status_code == 200, my_summary.text
    my_body = my_summary.json()
    assert my_body["student_id"] == student_doc_id
    assert my_body["attendance_percent"] == 50.0
    assert my_body["shortage_risk"] is True


def test_attendance_analytics_exposes_subject_breakdown_and_trend() -> None:
    fake_db = _setup_fake_db()
    fake_db.attendance_records = FakeUsersCollection()
    attendance_records_endpoint.db = fake_db
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_attendance_analytics@example.com")

    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Analytics Teacher",
            "email": "attendance_analytics_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Analytics Student",
            "email": "attendance_analytics_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "attendance_analytics_student@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    structure = _seed_canonical_structure(fake_db, suffix="ATA1", semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Analytics Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text

    subject_one = client.post(
        "/api/v1/subjects/",
        json={"name": "Networks", "code": "NW-ATA1", "description": "Networks"},
        headers=admin_headers,
    )
    subject_two = client.post(
        "/api/v1/subjects/",
        json={"name": "Operating Systems", "code": "OS-ATA1", "description": "OS"},
        headers=admin_headers,
    )
    assert subject_one.status_code == 201 and subject_two.status_code == 201

    offering_one = client.post(
        "/api/v1/course-offerings/",
        json={
            "subject_id": subject_one.json()["id"],
            "teacher_user_id": teacher.json()["id"],
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "section_id": section.json()["id"],
            "group_id": None,
            "academic_year": "2025-26",
            "offering_type": "theory",
        },
        headers=admin_headers,
    )
    offering_two = client.post(
        "/api/v1/course-offerings/",
        json={
            "subject_id": subject_two.json()["id"],
            "teacher_user_id": teacher.json()["id"],
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "section_id": section.json()["id"],
            "group_id": None,
            "academic_year": "2025-26",
            "offering_type": "theory",
        },
        headers=admin_headers,
    )
    assert offering_one.status_code == 201 and offering_two.status_code == 201

    slot_one = client.post(
        "/api/v1/class-slots/",
        json={
            "course_offering_id": offering_one.json()["id"],
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:00",
            "room_code": "A-201",
        },
        headers=admin_headers,
    )
    slot_two = client.post(
        "/api/v1/class-slots/",
        json={
            "course_offering_id": offering_two.json()["id"],
            "day": "Tuesday",
            "start_time": "10:00",
            "end_time": "11:00",
            "room_code": "A-202",
        },
        headers=admin_headers,
    )
    assert slot_one.status_code == 201 and slot_two.status_code == 201
    slot_one_id = str(fake_db.class_slots.items[-2]["_id"])
    slot_two_id = str(fake_db.class_slots.items[-1]["_id"])

    existing_student = next(
        (
            item
            for item in fake_db.students.items
            if item.get("user_id") == student.json()["id"] or item.get("email") == "attendance_analytics_student@example.com"
        ),
        None,
    )
    assert existing_student is not None
    existing_student.update(
        {
            "full_name": "Analytics Student",
            "roll_number": "ATA1-001",
            "email": "attendance_analytics_student@example.com",
            "user_id": student.json()["id"],
            "class_id": section.json()["id"],
            "is_active": True,
        }
    )
    student_doc_id = str(existing_student["_id"])

    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section.json()["id"], "student_id": student_doc_id},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    fake_db.attendance_records.items.extend(
        [
            {
                "_id": ObjectId(),
                "class_slot_id": slot_one_id,
                "student_id": student_doc_id,
                "status": "present",
                "marked_by_user_id": admin_headers["Authorization"],
                "marked_at": datetime.now(timezone.utc) - timedelta(days=3),
                "is_active": True,
            },
            {
                "_id": ObjectId(),
                "class_slot_id": slot_two_id,
                "student_id": student_doc_id,
                "status": "absent",
                "marked_by_user_id": admin_headers["Authorization"],
                "marked_at": datetime.now(timezone.utc) - timedelta(days=10),
                "is_active": True,
            },
        ]
    )

    analytics = client.get(
        f"/api/v1/attendance-records/analytics?section_id={section.json()['id']}&range_days=30&shortage_threshold=75",
        headers=admin_headers,
    )
    assert analytics.status_code == 200, analytics.text
    body = analytics.json()
    assert body["total_marked_slots"] == 2
    assert body["average_attendance_percent"] == 50.0
    assert len(body["subjects"]) == 2
    assert {item["subject_name"] for item in body["subjects"]} == {"Networks", "Operating Systems"}
    assert len(body["trend"]) >= 2

    my_analytics = client.get("/api/v1/attendance-records/my-analytics?range_days=30", headers=student_headers)
    assert my_analytics.status_code == 200, my_analytics.text
    my_body = my_analytics.json()
    assert my_body["student_id"] == student_doc_id
    assert my_body["total_marked_slots"] == 2
    assert my_body["shortage_risk"] is True


def test_published_timetable_reports_drift_against_class_slots() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_timetable_drift@example.com")

    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Drift Teacher",
            "email": "timetable_drift_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Drift Student",
            "email": "timetable_drift_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "timetable_drift_student@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    structure = _seed_canonical_structure(fake_db, suffix="TTD1", semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Drift Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Computer Networks", "code": "CN-TTD1", "description": "CN"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text

    offering = client.post(
        "/api/v1/course-offerings/",
        json={
            "subject_id": subject.json()["id"],
            "teacher_user_id": teacher.json()["id"],
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "section_id": section.json()["id"],
            "group_id": None,
            "academic_year": "2025-26",
            "offering_type": "theory",
        },
        headers=admin_headers,
    )
    assert offering.status_code == 201, offering.text

    slot = client.post(
        "/api/v1/class-slots/",
        json={
            "course_offering_id": offering.json()["id"],
            "day": "Monday",
            "start_time": "08:30",
            "end_time": "09:20",
            "room_code": "N-201",
        },
        headers=admin_headers,
    )
    assert slot.status_code == 201, slot.text

    existing_student = next(
        (
            item
            for item in fake_db.students.items
            if item.get("user_id") == student.json()["id"] or item.get("email") == "timetable_drift_student@example.com"
        ),
        None,
    )
    if existing_student is not None:
        existing_student.update(
            {
                "full_name": "Drift Student",
                "roll_number": "TTD1-001",
                "email": "timetable_drift_student@example.com",
                "user_id": student.json()["id"],
                "class_id": section.json()["id"],
                "is_active": True,
            }
        )
        student_doc_id = str(existing_student["_id"])
    else:
        student_profile = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Drift Student",
                "roll_number": "TTD1-001",
                "email": "timetable_drift_student@example.com",
                "user_id": student.json()["id"],
                "class_id": section.json()["id"],
            },
            headers=admin_headers,
        )
        assert student_profile.status_code == 201, student_profile.text
        student_doc_id = student_profile.json()["id"]

    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section.json()["id"], "student_id": student_doc_id},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    draft = client.post(
        "/api/v1/timetables/",
        json={
            "class_id": section.json()["id"],
            "semester": "SEM-2",
            "shift_id": "shift_1",
            "days": ["Monday"],
            "entries": [
                {
                    "day": "Monday",
                    "slot_key": "p1",
                    "subject_id": subject.json()["id"],
                    "teacher_user_id": teacher.json()["id"],
                    "room_code": "N-201",
                    "session_type": "theory",
                }
            ],
        },
        headers=admin_headers,
    )
    assert draft.status_code == 201, draft.text

    published = client.post(f"/api/v1/timetables/{draft.json()['id']}/publish", headers=admin_headers)
    assert published.status_code == 200, published.text
    published_body = published.json()["timetable"]
    assert published_body["sync_status"] == "synced"
    assert published_body["drift_count"] == 0

    slot_update = client.put(
        f"/api/v1/class-slots/{slot.json()['id']}",
        json={"room_code": "N-999"},
        headers=admin_headers,
    )
    assert slot_update.status_code == 200, slot_update.text

    student_timetable = client.get("/api/v1/timetables/my?semester=SEM-2", headers=student_headers)
    assert student_timetable.status_code == 200, student_timetable.text
    student_body = student_timetable.json()
    assert student_body["sync_status"] == "drifted"
    assert student_body["drift_count"] >= 1
    assert student_body["expected_class_slot_count"] == 1


def test_section_dashboard_summarizes_operational_health() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_section_dashboard@example.com")

    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Dashboard Teacher",
            "email": "section_dashboard_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Dashboard Student",
            "email": "section_dashboard_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "section_dashboard_student@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    structure = _seed_canonical_structure(fake_db, suffix="SDH1", semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Dashboard Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Software Testing", "code": "ST-SDH1", "description": "ST"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text

    offering = client.post(
        "/api/v1/course-offerings/",
        json={
            "subject_id": subject.json()["id"],
            "teacher_user_id": teacher.json()["id"],
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "section_id": section.json()["id"],
            "group_id": None,
            "academic_year": "2025-26",
            "offering_type": "theory",
        },
        headers=admin_headers,
    )
    assert offering.status_code == 201, offering.text

    slot = client.post(
        "/api/v1/class-slots/",
        json={
            "course_offering_id": offering.json()["id"],
            "day": "Monday",
            "start_time": "08:30",
            "end_time": "09:20",
            "room_code": "QA-101",
        },
        headers=admin_headers,
    )
    assert slot.status_code == 201, slot.text

    existing_student = next(
        (
            item
            for item in fake_db.students.items
            if item.get("user_id") == student.json()["id"] or item.get("email") == "section_dashboard_student@example.com"
        ),
        None,
    )
    if existing_student is not None:
        existing_student.update(
            {
                "full_name": "Dashboard Student",
                "roll_number": "SDH1-001",
                "email": "section_dashboard_student@example.com",
                "user_id": student.json()["id"],
                "class_id": section.json()["id"],
                "is_active": True,
            }
        )
        student_doc_id = str(existing_student["_id"])
    else:
        student_profile = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Dashboard Student",
                "roll_number": "SDH1-001",
                "email": "section_dashboard_student@example.com",
                "user_id": student.json()["id"],
                "class_id": section.json()["id"],
            },
            headers=admin_headers,
        )
        assert student_profile.status_code == 201, student_profile.text
        student_doc_id = student_profile.json()["id"]

    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section.json()["id"], "student_id": student_doc_id},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Dashboard Assignment", "description": "Desc", "total_marks": 100},
        headers=admin_headers,
    )
    assert assignment.status_code == 201
    submission = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("dashboard.txt", b"dashboard evaluation content", "text/plain")},
        headers=student_headers,
    )
    assert submission.status_code == 201

    evaluation = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission.json()["id"],
            "attendance_percent": 88,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 15,
            "final_exam": 48,
            "is_finalized": True,
        },
        headers=admin_headers,
    )
    assert evaluation.status_code == 201, evaluation.text
    assert evaluation.json()["result_status"] == "finalized_unreleased"

    draft = client.post(
        "/api/v1/timetables/",
        json={
            "class_id": section.json()["id"],
            "semester": "SEM-2",
            "shift_id": "shift_1",
            "days": ["Monday"],
            "entries": [
                {
                    "day": "Monday",
                    "slot_key": "p1",
                    "subject_id": subject.json()["id"],
                    "teacher_user_id": teacher.json()["id"],
                    "room_code": "QA-101",
                    "session_type": "theory",
                }
            ],
        },
        headers=admin_headers,
    )
    assert draft.status_code == 201, draft.text
    published = client.post(f"/api/v1/timetables/{draft.json()['id']}/publish", headers=admin_headers)
    assert published.status_code == 200, published.text

    dashboard = client.get(f"/api/v1/sections/dashboard?batch_id={structure['batch_id']}", headers=admin_headers)
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert body["total_sections"] >= 1
    section_item = next(item for item in body["sections"] if item["section_id"] == section.json()["id"])
    assert section_item["student_count"] == 1
    assert section_item["active_offering_count"] == 1
    assert section_item["unreleased_evaluation_count"] >= 1
    assert section_item["latest_timetable_sync_status"] == "synced"


def test_publish_semester_result_and_transcript_flow() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_semester_results@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="RES1", semester_number=3)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Semester Result Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Result Student",
            "email": "result_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "result_student@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Database Systems", "code": "DB-RES1", "description": "DB"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text

    existing_student = next(
        (
            item
            for item in fake_db.students.items
            if item.get("user_id") == student.json()["id"] or item.get("email") == "result_student@example.com"
        ),
        None,
    )
    if existing_student is not None:
        existing_student.update(
            {
                "full_name": "Result Student",
                "roll_number": "RES1-001",
                "email": "result_student@example.com",
                "user_id": student.json()["id"],
                "class_id": section.json()["id"],
                "is_active": True,
            }
        )
        student_doc_id = str(existing_student["_id"])
    else:
        student_profile = client.post(
            "/api/v1/students/",
            json={
                "full_name": "Result Student",
                "roll_number": "RES1-001",
                "email": "result_student@example.com",
                "user_id": student.json()["id"],
                "class_id": section.json()["id"],
            },
            headers=admin_headers,
        )
        assert student_profile.status_code == 201, student_profile.text
        student_doc_id = student_profile.json()["id"]

    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section.json()["id"], "student_id": student_doc_id},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    assignment = client.post(
        "/api/v1/assignments/",
        json={
            "title": "Semester Result Assignment",
            "description": "Desc",
            "subject_id": subject.json()["id"],
            "class_id": section.json()["id"],
            "total_marks": 100,
        },
        headers=admin_headers,
    )
    assert assignment.status_code == 201, assignment.text

    submission = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("semester-result.txt", b"semester result content", "text/plain")},
        headers=student_headers,
    )
    assert submission.status_code == 201, submission.text

    evaluation = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission.json()["id"],
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 48,
            "is_finalized": True,
        },
        headers=admin_headers,
    )
    assert evaluation.status_code == 201, evaluation.text

    released = client.patch(f"/api/v1/evaluations/{evaluation.json()['id']}/release", headers=admin_headers)
    assert released.status_code == 200, released.text

    published = client.post(
        f"/api/v1/evaluations/results/publish-from-evaluation/{evaluation.json()['id']}",
        headers=admin_headers,
    )
    assert published.status_code == 200, published.text
    result_body = published.json()
    assert result_body["status"] == "released"
    assert result_body["semester_id"] == structure["semester_id"]
    assert result_body["result_count"] >= 1
    assert result_body["gpa"] > 0

    transcript = client.get("/api/v1/evaluations/results/transcript", headers=student_headers)
    assert transcript.status_code == 200, transcript.text
    transcript_body = transcript.json()
    assert transcript_body["semester_count"] >= 1
    assert transcript_body["cgpa"] > 0

    correction_requested = client.post(
        f"/api/v1/evaluations/results/request-correction-from-evaluation/{evaluation.json()['id']}",
        json={"reason": "Result moderation review requested"},
        headers=admin_headers,
    )
    assert correction_requested.status_code == 200, correction_requested.text
    assert correction_requested.json()["status"] == "correction_requested"

    reopened = client.post(
        f"/api/v1/evaluations/results/{result_body['id']}/reopen",
        json={"reason": "Marks moderation required"},
        headers=admin_headers,
    )
    assert reopened.status_code == 200, reopened.text
    assert reopened.json()["status"] == "reopened"


def test_released_evaluation_change_flags_semester_result_for_correction() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_semester_correction@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="RES2", semester_number=5)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Semester Correction Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Correction Student",
            "email": "correction_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "correction_student@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Distributed Systems", "code": "DS-RES2", "description": "DS"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text

    existing_student = next(
        (item for item in fake_db.students.items if item.get("email") == "correction_student@example.com"),
        None,
    )
    existing_student.update(
        {
            "full_name": "Correction Student",
            "roll_number": "RES2-001",
            "email": "correction_student@example.com",
            "user_id": student.json()["id"],
            "class_id": section.json()["id"],
            "is_active": True,
        }
    )
    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section.json()["id"], "student_id": str(existing_student["_id"])},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    assignment = client.post(
        "/api/v1/assignments/",
        json={
            "title": "Correction Assignment",
            "description": "Desc",
            "subject_id": subject.json()["id"],
            "class_id": section.json()["id"],
            "total_marks": 100,
        },
        headers=admin_headers,
    )
    assert assignment.status_code == 201, assignment.text

    submission = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("correction.txt", b"correction content", "text/plain")},
        headers=student_headers,
    )
    assert submission.status_code == 201, submission.text

    evaluation = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission.json()["id"],
            "attendance_percent": 88,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 48,
            "is_finalized": True,
        },
        headers=admin_headers,
    )
    assert evaluation.status_code == 201, evaluation.text

    released = client.patch(f"/api/v1/evaluations/{evaluation.json()['id']}/release", headers=admin_headers)
    assert released.status_code == 200, released.text

    published = client.post(
        f"/api/v1/evaluations/results/publish-from-evaluation/{evaluation.json()['id']}",
        headers=admin_headers,
    )
    assert published.status_code == 200, published.text

    updated = client.put(
        f"/api/v1/evaluations/{evaluation.json()['id']}",
        json={"report": 9},
        headers=admin_headers,
    )
    assert updated.status_code == 200, updated.text

    results = client.get(
        "/api/v1/evaluations/results/summary",
        params={"student_user_id": student.json()["id"]},
        headers=admin_headers,
    )
    assert results.status_code == 200, results.text
    assert results.json()[0]["status"] == "correction_requested"


def test_exam_core_create_and_student_visibility() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_exam_core@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="EXM1", semester_number=4)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Exam Core Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Operating Systems", "code": "OS-EXM1", "description": "OS"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text

    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Exam Teacher",
            "email": "exam_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher.status_code == 201
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "exam_teacher@example.com", "password": "password123"},
    )
    assert teacher_login.status_code == 200
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    student_headers = _student_headers(client, "exam_student@example.com")
    student_user = next(item for item in fake_db.users.items if item.get("email") == "exam_student@example.com")
    student_profile = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Exam Student",
            "roll_number": "EXM1-001",
            "email": "exam_student@example.com",
            "user_id": str(student_user["_id"]),
            "class_id": section.json()["id"],
        },
        headers=admin_headers,
    )
    assert student_profile.status_code == 201, student_profile.text
    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section.json()["id"], "student_id": student_profile.json()["id"]},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    exam = client.post(
        "/api/v1/exams/",
        json={
            "title": "Operating Systems Midterm",
            "code": "OS-MID-1",
            "subject_id": subject.json()["id"],
            "batch_id": structure["batch_id"],
            "semester_id": structure["semester_id"],
            "section_id": section.json()["id"],
            "teacher_user_id": teacher.json()["id"],
            "exam_type": "midterm",
            "scheduled_for": "2026-05-10T10:00:00Z",
            "duration_minutes": 90,
            "room_code": "EX-201",
            "max_marks": 100,
            "status": "scheduled",
        },
        headers=admin_headers,
    )
    assert exam.status_code == 201, exam.text

    teacher_visible = client.get("/api/v1/exams/", headers=teacher_headers)
    assert teacher_visible.status_code == 200, teacher_visible.text
    assert any(item["id"] == exam.json()["id"] for item in teacher_visible.json())

    student_visible = client.get("/api/v1/exams/", headers=student_headers)
    assert student_visible.status_code == 200, student_visible.text
    assert any(item["id"] == exam.json()["id"] for item in student_visible.json())


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


def test_submission_upload_stores_similarity_retrieval_artifact() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_artifact@example.com")

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Artifact Assignment", "description": "artifact"},
        headers=headers,
    )
    assert assignment.status_code == 201

    student_headers = _student_headers(client, "student_similarity_artifact@example.com")
    uploaded = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("artifact.txt", b"validation regularization gradient tracking", "text/plain")},
        headers=student_headers,
    )
    assert uploaded.status_code == 201

    stored = fake_db.submissions.items[0]
    artifact = stored.get("similarity_retrieval_artifact")
    assert isinstance(artifact, dict)
    assert artifact["token_count"] > 0
    assert artifact["terms"]
    assert stored.get("updated_at") is not None


def test_similarity_detail_and_review_update() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_detail@example.com")

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Similarity Detail Assignment", "description": "detail"},
        headers=headers,
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]

    student_one_headers = _student_headers(client, "student_similarity_detail_one@example.com")
    student_two_headers = _student_headers(client, "student_similarity_detail_two@example.com")

    first = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("one.txt", b"identical detail similarity text", "text/plain")},
        headers=student_one_headers,
    )
    second = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("two.txt", b"identical detail similarity text", "text/plain")},
        headers=student_two_headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    run = client.post(
        f"/api/v1/similarity/checks/run/{first.json()['id']}?threshold=0.1",
        headers=headers,
    )
    assert run.status_code == 200
    log_id = run.json()[0]["id"]

    detail = client.get(f"/api/v1/similarity/checks/{log_id}", headers=headers)
    assert detail.status_code == 200
    body = detail.json()
    assert body["id"] == log_id
    assert body["is_flagged"] is True
    assert body["candidate_count"] is not None
    assert body["cap_reached"] in [True, False]
    assert isinstance(body.get("evidence_excerpts", []), list)
    assert body.get("overlap_stats") is not None

    update = client.patch(
        f"/api/v1/similarity/checks/{log_id}",
        json={"review_status": "in_progress", "review_notes": "Investigating."},
        headers=headers,
    )
    assert update.status_code == 200
    updated = update.json()
    assert updated["review_status"] == "in_progress"
    assert updated["review_notes"] == "Investigating."


def test_similarity_run_captures_semantic_shadow_for_top_unflagged_candidate() -> None:
    _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_shadow@example.com")

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Similarity Shadow Assignment", "description": "shadow"},
        headers=headers,
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]

    student_one_headers = _student_headers(client, "student_similarity_shadow_one@example.com")
    student_two_headers = _student_headers(client, "student_similarity_shadow_two@example.com")

    first = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("one.txt", b"neural network optimization uses validation feedback and regularization", "text/plain")},
        headers=student_one_headers,
    )
    second = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("two.txt", b"model training improves when validation checks and regularization are applied", "text/plain")},
        headers=student_two_headers,
    )
    assert first.status_code == 201
    assert second.status_code == 201

    run = client.post(
        f"/api/v1/similarity/checks/run/{first.json()['id']}?threshold=1.0",
        headers=headers,
    )
    assert run.status_code == 200
    body = run.json()
    assert body[0]["is_flagged"] is False
    assert body[0]["semantic_shadow_score"] is not None


def test_similarity_run_backfills_retrieval_artifacts_for_seeded_candidates() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_backfill@example.com")

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Artifact Backfill Assignment", "description": "backfill"},
        headers=headers,
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]

    student_headers = _student_headers(client, "student_similarity_backfill@example.com")
    source = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("source.txt", b"neural network optimization validation regularization", "text/plain")},
        headers=student_headers,
    )
    assert source.status_code == 201

    seeded_submission_id = ObjectId()
    fake_db.submissions.items.append(
        {
            "_id": seeded_submission_id,
            "assignment_id": assignment_id,
            "student_user_id": "seeded-artifact-student",
            "original_filename": "seeded.txt",
            "stored_filename": "seeded.txt",
            "content_type": "text/plain",
            "file_size_bytes": 64,
            "notes": None,
            "extracted_text": "validation regularization makes neural optimization stable",
            "similarity_score": None,
            "ai_status": "pending",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "schema_version": 1,
        }
    )

    run = client.post(f"/api/v1/similarity/checks/run/{source.json()['id']}?threshold=0.8", headers=headers)
    assert run.status_code == 200, run.text

    seeded_submission = next(item for item in fake_db.submissions.items if item.get("_id") == seeded_submission_id)
    assert seeded_submission.get("similarity_retrieval_artifact") is not None
    assert seeded_submission["similarity_retrieval_artifact"]["terms"]


def test_semantic_shadow_calibration_gate_passes_default_cases() -> None:
    report = run_semantic_shadow_calibration()

    assert report["gates"]["passed"] is True
    assert report["summary"]["case_count"] >= 4
    assert report["summary"]["failed_count"] == 0


def test_fairness_regression_gate_passes_default_cases() -> None:
    report = run_fairness_regression_suite()

    assert report["gates"]["passed"] is True
    assert report["summary"]["check_count"] >= 6
    assert report["summary"]["failed_count"] == 0
    assert "max_unicode_eval_delta" in report["thresholds"]
    assert "max_short_answer_delta" in report["thresholds"]
    assert "max_rubric_shape_delta" in report["thresholds"]


def test_reviewer_outcome_calibration_report_promotes_only_with_real_review_separation() -> None:
    fake_db = _setup_fake_db()
    now = datetime.now(timezone.utc)
    seeded_logs = [
        {"score": 0.48, "semantic_shadow_score": 0.82, "review_status": "fixed", "review_notes": "Confirmed paraphrase evidence."},
        {"score": 0.51, "semantic_shadow_score": 0.84, "review_status": "fixed", "review_notes": "Semantic drift supported manual confirmation."},
        {"score": 0.55, "semantic_shadow_score": 0.79, "review_status": "fixed", "review_notes": "Strong excerpt evidence after review."},
        {"score": 0.32, "semantic_shadow_score": 0.39, "review_status": "reopened", "review_notes": "Insufficient evidence after manual review."},
        {"score": 0.29, "semantic_shadow_score": 0.35, "review_status": "reopened", "review_notes": "Likely template overlap from common prompt language."},
        {"score": 0.44, "semantic_shadow_score": 0.61, "review_status": "in_progress", "review_notes": "Needs reviewer follow-up."},
    ]
    for index, item in enumerate(seeded_logs):
        fake_db.similarity_logs.items.append(
            {
                "_id": ObjectId(),
                "source_submission_id": f"source-{index}",
                "matched_submission_id": f"matched-{index}",
                "score": item["score"],
                "semantic_shadow_score": item["semantic_shadow_score"],
                "review_status": item["review_status"],
                "review_notes": item["review_notes"],
                "is_flagged": True,
                "created_at": now - timedelta(minutes=index),
                "reviewed_at": now - timedelta(days=(2 - min(index, 2))) if item["review_status"] == "fixed" else now - timedelta(days=1),
            }
        )

    report = asyncio.run(build_reviewer_outcome_calibration_report(database=fake_db))

    assert report["summary"]["reviewed_final_count"] == 5
    assert report["summary"]["fixed_count"] == 3
    assert report["summary"]["reopened_count"] == 2
    assert report["gates"]["promotion_ready"] is True
    assert report["recommendations"]["keep_shadow_only"] is True
    assert report["recommendations"]["promotion_thresholds"]["semantic_advantage_min"] >= 0.1
    assert report["analytics"]["review_status_counts"]["fixed"] == 3
    assert any(bucket["count"] > 0 for bucket in report["analytics"]["drift_buckets"])
    assert report["analytics"]["top_reopened_reasons"][0]["count"] >= 1
    assert report["analytics"]["reopened_reason_trends"][0]["trend_symbol"] in {"↑", "↓", "→"}
    assert report["analytics"]["reopened_reason_trends"][0]["recent_count"] >= 0
    assert len(report["analytics"]["threshold_trend"]) >= 2


def test_reviewer_outcome_calibration_report_handles_empty_similarity_logs() -> None:
    fake_db = _setup_fake_db()

    report = asyncio.run(build_reviewer_outcome_calibration_report(database=fake_db))

    assert report["summary"]["logs_considered"] == 0
    assert report["summary"]["reviewed_final_count"] == 0
    assert report["summary"]["latest_reviewed_at"] is None
    assert report["recommendations"]["assist_only_semantic_advantage_threshold"] == 0.15
    assert report["gates"]["promotion_ready"] is False
    assert len(report["gates"]["failures"]) == 2
    assert report["analytics"]["review_status_counts"]["reopened"] == 0
    assert report["analytics"]["drift_buckets"][0]["count"] == 0
    assert report["analytics"]["top_reopened_reasons"] == []
    assert report["analytics"]["reopened_reason_trends"] == []
    assert report["analytics"]["threshold_trend"] == []


def test_ai_operations_overview_includes_quality_gate_snapshot() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_ai_ops_quality@example.com")
    now = datetime.now(timezone.utc)
    fake_db.similarity_logs.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_submission_id": "source-fixed",
                "matched_submission_id": "matched-fixed",
                "score": 0.49,
                "semantic_shadow_score": 0.81,
                "review_status": "fixed",
                "review_notes": "Confirmed semantic overlap.",
                "is_flagged": True,
                "created_at": now,
                "reviewed_at": now,
            },
            {
                "_id": ObjectId(),
                "source_submission_id": "source-reopened",
                "matched_submission_id": "matched-reopened",
                "score": 0.31,
                "semantic_shadow_score": 0.37,
                "review_status": "reopened",
                "review_notes": "Insufficient evidence after manual review.",
                "is_flagged": True,
                "created_at": now - timedelta(minutes=1),
                "reviewed_at": now - timedelta(minutes=1),
            },
        ]
    )

    response = client.get("/api/v1/ai/ops/overview", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "quality_gates" in body
    assert "semantic_calibration" in body["quality_gates"]
    assert "fairness_regression" in body["quality_gates"]
    assert "benchmark" in body["quality_gates"]
    assert body["quality_gates"]["reviewer_outcome_calibration"]["summary"]["reviewed_final_count"] == 2
    assert "analytics" in body["quality_gates"]["reviewer_outcome_calibration"]
    assert body["quality_gates"]["reviewer_outcome_calibration"]["analytics"]["review_status_counts"]["fixed"] == 1
    assert "reopened_reason_trends" in body["quality_gates"]["reviewer_outcome_calibration"]["analytics"]


def test_similarity_checks_support_review_filters_and_search() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_filters@example.com")
    now = datetime.now(timezone.utc)
    fake_db.similarity_logs.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_submission_id": "sub-fixed-drift",
                "matched_submission_id": "sub-target-1",
                "score": 0.42,
                "semantic_shadow_score": 0.68,
                "review_status": "fixed",
                "review_notes": "Confirmed after semantic drift review.",
                "cap_reached": True,
                "extraction_quality": {"source": 0.81, "matched": 0.77},
                "is_flagged": True,
                "created_at": now,
            },
            {
                "_id": ObjectId(),
                "source_submission_id": "sub-reopened-lowtext",
                "matched_submission_id": "sub-target-2",
                "score": 0.39,
                "semantic_shadow_score": 0.43,
                "review_status": "reopened",
                "review_notes": "Insufficient evidence because extraction was weak.",
                "cap_reached": False,
                "extraction_quality": {"source": 0.31, "matched": 0.48},
                "is_flagged": True,
                "created_at": now - timedelta(minutes=1),
            },
            {
                "_id": ObjectId(),
                "source_submission_id": "sub-open-mid",
                "matched_submission_id": "sub-target-3",
                "score": 0.61,
                "semantic_shadow_score": 0.66,
                "review_status": "open",
                "review_notes": "Pending review.",
                "cap_reached": False,
                "extraction_quality": {"source": 0.74, "matched": 0.71},
                "is_flagged": True,
                "created_at": now - timedelta(minutes=2),
            },
        ]
    )

    drift_filtered = client.get(
        "/api/v1/similarity/checks?is_flagged=true&review_status=fixed&semantic_drift_present=true&cap_reached=true&min_score=0.4&max_score=0.5&search=semantic",
        headers=headers,
    )
    assert drift_filtered.status_code == 200, drift_filtered.text
    drift_body = drift_filtered.json()
    assert len(drift_body) == 1
    assert drift_body[0]["source_submission_id"] == "sub-fixed-drift"

    low_quality_filtered = client.get(
        "/api/v1/similarity/checks?is_flagged=true&review_status=reopened&low_extraction_quality=true&search=weak",
        headers=headers,
    )
    assert low_quality_filtered.status_code == 200, low_quality_filtered.text
    low_quality_body = low_quality_filtered.json()
    assert len(low_quality_body) == 1
    assert low_quality_body[0]["source_submission_id"] == "sub-reopened-lowtext"
    assert low_quality_body[0]["extraction_quality"]["source"] == 0.31


def test_similarity_review_update_persists_structured_reopened_reason() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_review_reason@example.com")
    log_id = ObjectId()
    fake_db.similarity_logs.items.append(
        {
            "_id": log_id,
            "source_submission_id": "sub-review-reason-source",
            "matched_submission_id": "sub-review-reason-match",
            "score": 0.44,
            "semantic_shadow_score": 0.61,
            "review_status": "open",
            "review_notes": "",
            "is_flagged": True,
            "created_at": datetime.now(timezone.utc),
        }
    )

    response = client.patch(
        f"/api/v1/similarity/checks/{log_id}",
        headers=headers,
        json={
            "review_status": "reopened",
            "review_reason_code": "extraction_quality",
            "review_notes": "Reopened because the PDF text extraction was too weak to trust."
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["review_status"] == "reopened"
    assert body["review_reason_code"] == "extraction_quality"
    assert body["review_notes"].startswith("Reopened because")
    stored = next(item for item in fake_db.similarity_logs.items if item["_id"] == log_id)
    assert stored["review_reason_code"] == "extraction_quality"

    clear_response = client.patch(
        f"/api/v1/similarity/checks/{log_id}",
        headers=headers,
        json={"review_status": "fixed", "review_notes": "Confirmed after manual review."},
    )
    assert clear_response.status_code == 200, clear_response.text
    cleared_body = clear_response.json()
    assert cleared_body["review_status"] == "fixed"
    assert cleared_body["review_reason_code"] is None


def test_ai_ops_similarity_views_are_shared_and_admin_deletable() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    teacher_one_headers = _teacher_headers(client, "teacher_similarity_views_one@example.com")
    teacher_two_headers = _teacher_headers(client, "teacher_similarity_views_two@example.com")
    admin_headers = _admin_headers(client, "admin_similarity_views@example.com")

    create_response = client.post(
        "/api/v1/ai/ops/similarity/views",
        headers=teacher_one_headers,
        json={
            "name": "Reopened + low extraction",
            "filters": {
                "review_status": "reopened",
                "low_extraction_quality": True,
                "semantic_drift_present": False,
                "cap_reached": False,
                "search": "",
                "min_score": None,
                "max_score": None,
            },
        },
    )
    assert create_response.status_code == 201, create_response.text
    created = create_response.json()
    assert created["name"] == "Reopened + low extraction"
    assert created["filters"]["review_status"] == "reopened"
    assert created["filters"]["low_extraction_quality"] is True

    list_response = client.get("/api/v1/ai/ops/similarity/views", headers=teacher_two_headers)
    assert list_response.status_code == 200, list_response.text
    rows = list_response.json()
    assert len(rows) == 1
    assert rows[0]["id"] == created["id"]
    assert rows[0]["created_by_label"] == "Teacher User"

    forbidden_delete = client.delete(f"/api/v1/ai/ops/similarity/views/{created['id']}", headers=teacher_two_headers)
    assert forbidden_delete.status_code == 404, forbidden_delete.text

    admin_delete = client.delete(f"/api/v1/ai/ops/similarity/views/{created['id']}", headers=admin_headers)
    assert admin_delete.status_code == 200, admin_delete.text
    assert admin_delete.json()["deleted"] is True
    assert fake_db.ai_similarity_views.items == []


def test_ai_operations_overview_includes_similarity_queue_metrics() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_queue_metrics@example.com")
    now = datetime.now(timezone.utc)
    fake_db.similarity_logs.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_submission_id": "sub-open-low",
                "matched_submission_id": "sub-match-1",
                "score": 0.41,
                "semantic_shadow_score": 0.44,
                "review_status": "open",
                "review_notes": "Needs reviewer follow-up.",
                "extraction_quality": {"source": 0.32, "matched": 0.61},
                "is_flagged": True,
                "created_at": now - timedelta(hours=48),
            },
            {
                "_id": ObjectId(),
                "source_submission_id": "sub-reopened",
                "matched_submission_id": "sub-match-2",
                "score": 0.47,
                "semantic_shadow_score": 0.52,
                "review_status": "reopened",
                "review_notes": "Reopened after manual review.",
                "extraction_quality": {"source": 0.79, "matched": 0.74},
                "is_flagged": True,
                "created_at": now - timedelta(hours=24),
            },
            {
                "_id": ObjectId(),
                "source_submission_id": "sub-high-drift",
                "matched_submission_id": "sub-match-3",
                "score": 0.33,
                "semantic_shadow_score": 0.61,
                "review_status": "open",
                "review_notes": "High semantic drift needs review.",
                "cap_reached": True,
                "extraction_quality": {"source": 0.82, "matched": 0.78},
                "is_flagged": True,
                "created_at": now - timedelta(hours=12),
            },
        ]
    )
    fake_db.ai_similarity_views.items.append(
        {
            "_id": ObjectId(),
            "library_key": "staff",
            "name": "Needs review + low extraction",
            "filters": {
                "review_status": "open",
                "low_extraction_quality": True,
                "semantic_drift_present": False,
                "cap_reached": False,
                "search": "",
                "min_score": None,
                "max_score": None,
            },
            "created_by_user_id": None,
            "created_at": now,
            "updated_at": now,
        }
    )

    response = client.get("/api/v1/ai/ops/overview", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "similarity_queue_metrics" in body
    default_metrics = {item["id"]: item for item in body["similarity_queue_metrics"]["default_queues"]}
    assert default_metrics["all"]["count"] == 3
    assert default_metrics["needs-review"]["count"] == 2
    assert default_metrics["reopened"]["count"] == 1
    assert default_metrics["low-text-risk"]["count"] == 1
    assert default_metrics["high-drift"]["count"] == 1
    assert default_metrics["cap-reached"]["count"] == 1
    assert default_metrics["low-text-risk"]["low_extraction_rate"] == 1.0
    assert default_metrics["all"]["average_age_hours"] is not None

    shared_metrics = body["similarity_queue_metrics"]["shared_views"]
    assert len(shared_metrics) == 1
    assert shared_metrics[0]["label"] == "Needs review + low extraction"
    assert shared_metrics[0]["count"] == 1


def test_ai_operations_overview_includes_similarity_queue_forecast() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_queue_forecast@example.com")
    now = datetime.now(timezone.utc)
    for index in range(8):
        fake_db.similarity_logs.items.append(
            {
                "_id": ObjectId(),
                "source_submission_id": f"forecast-source-{index}",
                "matched_submission_id": f"forecast-match-{index}",
                "score": 0.41,
                "semantic_shadow_score": 0.58,
                "review_status": "open",
                "review_notes": "Queue forecast regression coverage.",
                "is_flagged": True,
                "created_at": now - timedelta(hours=30 if index == 0 else 4),
            }
        )

    response = client.get("/api/v1/ai/ops/overview", headers=headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert "similarity_queue_forecast" in body
    forecast_by_id = {item["id"]: item for item in body["similarity_queue_forecast"]["default_queues"]}
    assert forecast_by_id["all"]["backlog_risk"] == "medium"
    assert forecast_by_id["all"]["attention_badge"] is True
    assert forecast_by_id["all"]["oldest_age_hours"] is not None


def test_submission_upload_persists_extraction_diagnostics() -> None:
    _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_submission_ocr_diag@example.com")
    student_headers = _student_headers(client, "student_submission_ocr_diag@example.com")

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "OCR Diagnostic Assignment", "description": "Desc", "total_marks": 100},
        headers=admin_headers,
    )
    assert assignment.status_code == 201

    original_parse = submissions_endpoint.parse_file_content_with_diagnostics
    submissions_endpoint.parse_file_content_with_diagnostics = lambda filename, content: ParsedFileResult(
        text="",
        extraction_diagnostics={
            "ocr_attempted": True,
            "ocr_provider": "mock_echo",
            "ocr_chars_added": 24,
            "page_count": 2,
            "extraction_confidence": 0.34,
            "low_text_reason": "empty_pdf_text",
            "parser": "pdf",
        },
    )
    try:
        upload = client.post(
            "/api/v1/submissions/upload",
            data={"assignment_id": assignment.json()["id"]},
            files={"file": ("scan.pdf", b"%PDF-1.4 mock", "application/pdf")},
            headers=student_headers,
        )
    finally:
        submissions_endpoint.parse_file_content_with_diagnostics = original_parse

    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["ocr_attempted"] is True
    assert body["ocr_provider"] == "mock_echo"
    assert body["ocr_chars_added"] == 24
    assert body["page_count"] == 2
    assert body["extraction_confidence"] == 0.34
    assert body["low_text_reason"] == "empty_pdf_text"


def test_similarity_run_stores_cross_assignment_shadow_candidates_without_flagging() -> None:
    _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_cross_assignment_shadow@example.com")
    source_student_headers = _student_headers(client, "student_cross_assignment_source@example.com")
    same_assignment_headers = _student_headers(client, "student_cross_assignment_same@example.com")
    cross_assignment_headers = _student_headers(client, "student_cross_assignment_other@example.com")

    assignment_primary = client.post(
        "/api/v1/assignments/",
        json={"title": "Primary Assignment", "description": "Explain gradient descent and validation.", "total_marks": 100},
        headers=admin_headers,
    )
    assignment_other = client.post(
        "/api/v1/assignments/",
        json={"title": "Other Assignment", "description": "Cross-assignment shadow probe.", "total_marks": 100},
        headers=admin_headers,
    )
    assert assignment_primary.status_code == 201
    assert assignment_other.status_code == 201

    source_upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_primary.json()["id"]},
        files={"file": ("source.txt", b"Gradient descent uses validation data and regularization.", "text/plain")},
        headers=source_student_headers,
    )
    same_assignment_upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_primary.json()["id"]},
        files={"file": ("same.txt", b"Gradient descent uses validation data and regularization.", "text/plain")},
        headers=same_assignment_headers,
    )
    cross_assignment_upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_other.json()["id"]},
        files={"file": ("cross.txt", b"Validation data plus regularization support robust gradient descent updates.", "text/plain")},
        headers=cross_assignment_headers,
    )
    assert source_upload.status_code == 201
    assert same_assignment_upload.status_code == 201
    assert cross_assignment_upload.status_code == 201

    original_cross_assignment_enabled = settings.similarity_cross_assignment_enabled
    original_language_detection_enabled = settings.similarity_language_detection_enabled
    settings.similarity_cross_assignment_enabled = True
    settings.similarity_language_detection_enabled = True
    try:
        run = client.post(f"/api/v1/similarity/checks/run/{source_upload.json()['id']}?threshold=0.8", headers=admin_headers)
    finally:
        settings.similarity_cross_assignment_enabled = original_cross_assignment_enabled
        settings.similarity_language_detection_enabled = original_language_detection_enabled

    assert run.status_code == 200, run.text
    rows = run.json()
    flagged = next(item for item in rows if item["match_scope"] == "same_assignment_lexical")
    cross_shadow = next(item for item in rows if item["match_scope"] == "cross_assignment_shadow")
    assert flagged["is_flagged"] is True
    assert cross_shadow["is_flagged"] is False
    assert cross_shadow["language_profile"]["source"]["primary_script"] == "latin"

    detail = client.get(f"/api/v1/similarity/checks/{flagged['id']}", headers=admin_headers)
    assert detail.status_code == 200, detail.text
    detail_body = detail.json()
    assert any(item["match_scope"] == "cross_assignment_shadow" for item in detail_body["related_shadow_candidates"])


def test_evaluation_preview_and_persisted_payloads_share_rubric_criteria_outputs() -> None:
    _setup_fake_db()
    client = TestClient(app)
    headers = _admin_headers(client, "admin_eval_rubric_outputs@example.com")

    _assignment, upload, _student_headers_unused = _create_submission(
        client, headers, "student_eval_rubric_outputs@example.com", title="Rubric Outputs"
    )
    rubric_criteria = [
        {"label": "Concept clarity", "max_score": 5, "keywords": ["concept", "clarity"], "notes": "Explain the core idea clearly."},
        {"label": "Examples", "max_score": 5, "keywords": ["example", "evidence"], "notes": "Use an example or evidence."},
    ]

    preview = client.post(
        "/api/v1/evaluations/ai-preview",
        json={
            "submission_id": upload["id"],
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 48,
            "remarks": "Preview rubric parity",
            "rubric_criteria": rubric_criteria,
        },
        headers=headers,
    )
    assert preview.status_code == 200, preview.text
    preview_body = preview.json()
    assert preview_body["rubric_criteria"][0]["label"] == "Concept clarity"
    assert len(preview_body["ai_criterion_scores"]) == 2

    created = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": upload["id"],
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 48,
            "remarks": "Persist rubric parity",
            "rubric_criteria": rubric_criteria,
            "is_finalized": False,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    created_body = created.json()
    assert created_body["rubric_criteria"][0]["label"] == "Concept clarity"
    assert [item["label"] for item in created_body["ai_criterion_scores"]] == [
        item["label"] for item in preview_body["ai_criterion_scores"]
    ]
    assert created_body["ai_criterion_rationales"] == preview_body["ai_criterion_rationales"]


def test_chat_fallback_response_omits_numeric_hints() -> None:
    response, error, metadata = generate_evaluation_chat_reply(
        teacher_message="Help me review this answer.",
        question_text="Explain neural network optimization.",
        student_answer="Neural network optimization uses validation data and regularization.",
        rubric="Focus on correctness, clarity, and examples.",
        runtime_settings={"effective_provider_enabled": False},
    )
    assert error == "OpenAI key not configured"
    assert metadata["provider"] == "local"
    assert "Fallback Review Hint:" in response
    assert "/10" not in response
    assert "Teacher Action:" in response


def test_similarity_prefilter_limits_full_tfidf_candidates() -> None:
    source_text = "neural network optimization validation regularization gradient"
    candidate_texts = [
        (f"sub-{index}", f"candidate {index} unrelated coursework reflection text")
        for index in range(max(int(settings.similarity_prefilter_top_k), 5) + 30)
    ]
    candidate_texts[3] = ("sub-hit", "neural network validation and regularization guidance")

    filtered = prefilter_similarity_candidates(source_text, candidate_texts)

    assert len(filtered) == max(1, int(settings.similarity_prefilter_top_k))
    assert any(submission_id == "sub-hit" for submission_id, _text in filtered)


def test_similarity_sync_large_run_is_deferred_to_async_job() -> None:
    fake_db = _setup_fake_db()
    ai_jobs_service.db = fake_db
    client = TestClient(app)
    headers = _admin_headers(client, "admin_similarity_deferred@example.com")

    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Deferred Similarity Assignment", "description": "async guard"},
        headers=headers,
    )
    assert assignment.status_code == 201
    assignment_id = assignment.json()["id"]

    student_headers = _student_headers(client, "student_similarity_deferred@example.com")
    source = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_id},
        files={"file": ("source.txt", b"neural network optimization validation data", "text/plain")},
        headers=student_headers,
    )
    assert source.status_code == 201

    for index in range(max(int(settings.similarity_sync_inline_candidate_limit), 5) + 10):
        fake_db.submissions.items.append(
            {
                "_id": ObjectId(),
                "assignment_id": assignment_id,
                "student_user_id": f"bulk-student-{index}",
                "original_filename": f"bulk-{index}.txt",
                "stored_filename": f"bulk-{index}.txt",
                "content_type": "text/plain",
                "file_size_bytes": 64,
                "notes": None,
                "extracted_text": f"candidate {index} neural network validation text",
                "similarity_score": None,
                "ai_status": "pending",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "schema_version": 1,
            }
        )

    original_schedule = similarity_endpoint.schedule_ai_job_processing
    similarity_endpoint.schedule_ai_job_processing = lambda max_jobs=1: None
    try:
        run = client.post(f"/api/v1/similarity/checks/run/{source.json()['id']}?threshold=0.8", headers=headers)
        assert run.status_code == 202, run.text
        body = run.json()
        assert body["status"] == "queued"
        assert body["candidate_count"] > int(settings.similarity_sync_inline_candidate_limit)
        assert body["job"]["job_type"] == "similarity_check"

        asyncio.run(process_ai_jobs_once(max_jobs=1))
        assert fake_db.similarity_logs.items
    finally:
        similarity_endpoint.schedule_ai_job_processing = original_schedule


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


def test_future_scheduled_notice_stays_hidden_until_due_then_dispatches() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_future_schedule@example.com")
    student_headers = _student_headers(client, "student_future_schedule@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="FSCH", start_year=2024, semester_number=2)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Future Schedule Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201

    student_doc_id = ObjectId()
    fake_db.students.items.append(
        {
            "_id": student_doc_id,
            "full_name": "Future Schedule Student",
            "roll_number": "FSCH-001",
            "email": "student_future_schedule@example.com",
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

    future_time = datetime.now(timezone.utc) + timedelta(hours=2)

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

    original_send_email_batch = background_jobs_service.send_outbound_email_batch
    background_jobs_service.send_outbound_email_batch = successful_send_email_batch
    try:
        created = client.post(
            "/api/v1/notices/",
            json={
                "title": "Future Scheduled Notice",
                "message": "This should only appear after the scheduled time.",
                "priority": "normal",
                "scope": "class",
                "scope_ref_id": section.json()["id"],
                "scheduled_at": future_time.isoformat(),
            },
            headers=admin_headers,
        )
        assert created.status_code == 201, created.text
        created_body = created.json()
        assert created_body["fanout_status"] == "scheduled"
        assert created_body["fanout_count"] == 0

        admin_list = client.get("/api/v1/notices/?include_scheduled=true", headers=admin_headers)
        assert admin_list.status_code == 200, admin_list.text
        assert any(item["id"] == created_body["id"] for item in admin_list.json())

        student_before_due = client.get("/api/v1/notices/", headers=student_headers)
        assert student_before_due.status_code == 200, student_before_due.text
        assert all(item["id"] != created_body["id"] for item in student_before_due.json())

        notice_row = next(item for item in fake_db.notices.items if str(item["_id"]) == created_body["id"])
        notice_row["scheduled_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)

        dispatched = asyncio.run(background_jobs_service.dispatch_scheduled_notice_notifications(limit=10))
        assert dispatched == 1

        stored = next(item for item in fake_db.notices.items if str(item["_id"]) == created_body["id"])
        assert stored["fanout_status"] == "dispatched"
        assert stored["fanout_count"] == 1
        assert stored["fanout_dispatched_at"] is not None

        student_after_due = client.get("/api/v1/notices/", headers=student_headers)
        assert student_after_due.status_code == 200, student_after_due.text
        visible_notice = next(item for item in student_after_due.json() if item["id"] == created_body["id"])
        assert visible_notice["delivery_summary"]["total_recipients"] == 1
        assert visible_notice["delivery_summary"]["email"]["sent_count"] == 1
    finally:
        background_jobs_service.send_outbound_email_batch = original_send_email_batch


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


def test_admin_delivery_report_and_export_support_notice_filters_and_time_window_fallbacks() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_notice_delivery_report@example.com")

    now = datetime.now(timezone.utc)
    notice_id = ObjectId()
    other_notice_id = ObjectId()
    fake_db.notices.items.extend(
        [
            {
                "_id": notice_id,
                "public_id": "NOT-REPORT-001",
                "title": "System Notice Report",
                "message": "Primary notice for delivery report coverage",
                "scope": "system",
                "created_by": "creator-notice",
                "created_at": now,
                "is_active": True,
            },
            {
                "_id": other_notice_id,
                "public_id": "NOT-REPORT-002",
                "title": "Other Notice Report",
                "message": "Should be filtered out",
                "scope": "ai",
                "created_by": "creator-other",
                "created_at": now,
                "is_active": True,
            },
        ]
    )
    fake_db.communication_deliveries.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_kind": "notice",
                "source_id": str(notice_id),
                "source_public_id": "NOT-REPORT-001",
                "target_user_id": "user-1",
                "target_email": "user1@example.com",
                "channel": "email",
                "status": "sent",
                "sent_at": now,
                "metadata": {"delivery_mode": "instant"},
            },
            {
                "_id": ObjectId(),
                "source_kind": "notice",
                "source_id": str(notice_id),
                "source_public_id": "NOT-REPORT-001",
                "target_user_id": "user-2",
                "target_email": "user2@example.com",
                "channel": "email",
                "status": "read",
                "read_at": now,
                "metadata": {"delivery_mode": "instant"},
            },
            {
                "_id": ObjectId(),
                "source_kind": "notice",
                "source_id": str(notice_id),
                "source_public_id": "NOT-REPORT-001",
                "target_user_id": "user-3",
                "channel": "in_app",
                "status": "pending",
                "updated_at": now,
                "metadata": {"scope": "system"},
            },
            {
                "_id": ObjectId(),
                "source_kind": "notice",
                "source_id": str(notice_id),
                "source_public_id": "NOT-REPORT-001",
                "target_user_id": "user-old",
                "target_email": "old@example.com",
                "channel": "email",
                "status": "failed",
                "updated_at": now - timedelta(days=45),
                "error": "Old failure should be excluded",
            },
            {
                "_id": ObjectId(),
                "source_kind": "notice",
                "source_id": str(other_notice_id),
                "source_public_id": "NOT-REPORT-002",
                "target_user_id": "user-4",
                "target_email": "user4@example.com",
                "channel": "email",
                "status": "pending",
                "updated_at": now,
            },
        ]
    )

    report = client.get(
        "/api/v1/admin/communication/delivery/report?days=7&source_kind=notice&scope=system&created_by=creator-notice",
        headers=admin_headers,
    )
    assert report.status_code == 200, report.text
    body = report.json()
    assert body["total_rows"] == 3
    assert body["total_sources"] == 1
    assert body["sent_count"] == 2
    assert body["pending_count"] == 1
    assert body["failed_count"] == 0
    assert body["read_count"] == 1
    assert body["by_channel"]["email"] == 2
    assert body["by_channel"]["in_app"] == 1
    assert body["by_scope"]["system"] == 3
    assert body["creator_rows"][0]["key"] == "creator-notice"
    assert body["creator_rows"][0]["total_count"] == 3
    assert body["scope_rows"][0]["key"] == "system"
    assert body["email_health"]["total_rows"] == 2
    assert body["email_health"]["sent_count"] == 2
    assert body["email_health"]["read_count"] == 1
    assert body["email_health"]["delivered_rate_pct"] == 100

    report_export = client.get(
        "/api/v1/admin/communication/delivery/report/export?days=7&source_kind=notice&scope=system&created_by=creator-notice",
        headers=admin_headers,
    )
    assert report_export.status_code == 200, report_export.text
    assert "System Notice Report" in report_export.text
    assert "creator-notice" in report_export.text
    assert "user1@example.com" in report_export.text
    assert "user2@example.com" in report_export.text
    assert "NOT-REPORT-002" not in report_export.text
    assert "old@example.com" not in report_export.text

    creator_export = client.get(
        "/api/v1/admin/communication/delivery/report/export?days=7&source_kind=notice&scope=system&view=creator_summary",
        headers=admin_headers,
    )
    assert creator_export.status_code == 200, creator_export.text
    assert "creator-notice" in creator_export.text
    assert "total_count" in creator_export.text


def test_admin_delivery_report_distinguishes_read_status_filter_from_sent_rows() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_read_filter@example.com")

    now = datetime.now(timezone.utc)
    notification_id = ObjectId()
    fake_db.notifications.items.append(
        {
            "_id": notification_id,
            "public_id": "NTF-READ-001",
            "title": "Read Filter Notification",
            "message": "Validate read-only filtering",
            "scope": "system",
            "created_by": "creator-read",
            "created_at": now,
            "is_read": False,
        }
    )
    fake_db.communication_deliveries.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-READ-001",
                "target_user_id": "user-read",
                "target_email": "read@example.com",
                "channel": "email",
                "status": "read",
                "read_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-READ-001",
                "target_user_id": "user-sent",
                "target_email": "sent@example.com",
                "channel": "email",
                "status": "sent",
                "sent_at": now,
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-READ-001",
                "target_user_id": "user-pending",
                "channel": "in_app",
                "status": "pending",
                "updated_at": now,
            },
        ]
    )

    response = client.get(
        "/api/v1/admin/communication/delivery/report?days=7&source_kind=notification&scope=system&status=read&created_by=creator-read",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_rows"] == 1
    assert body["sent_count"] == 1
    assert body["read_count"] == 1
    assert body["pending_count"] == 0
    assert body["failed_count"] == 0
    assert body["by_status"]["read"] == 1
    assert "sent" not in body["by_status"]
    assert body["email_health"]["total_rows"] == 1
    assert body["email_health"]["read_count"] == 1

    export_response = client.get(
        "/api/v1/admin/communication/delivery/report/export?days=7&source_kind=notification&scope=system&status=read&created_by=creator-read",
        headers=admin_headers,
    )
    assert export_response.status_code == 200, export_response.text
    assert "read@example.com" in export_response.text
    assert "sent@example.com" not in export_response.text


def test_admin_delivery_report_export_rejects_unknown_view() -> None:
    _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_invalid_export@example.com")

    response = client.get(
        "/api/v1/admin/communication/delivery/report/export?days=7&source_kind=notification&view=unknown_view",
        headers=admin_headers,
    )
    assert response.status_code == 400, response.text
    assert response.json()["detail"] == "Unsupported export view"


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


def test_admin_delivery_report_benchmarks_compare_current_and_previous_window() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_benchmarks@example.com")

    now = datetime.now(timezone.utc)
    notification_id = ObjectId()
    fake_db.notifications.items.append(
        {
            "_id": notification_id,
            "public_id": "NTF-BENCH-001",
            "title": "Benchmark Notification",
            "message": "Benchmark target",
            "scope": "system",
            "created_by": "creator-benchmark",
            "created_at": now - timedelta(days=10),
            "is_read": False,
        }
    )
    fake_db.communication_deliveries.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-BENCH-001",
                "target_user_id": "current-sent",
                "channel": "email",
                "status": "sent",
                "updated_at": now - timedelta(days=1),
                "sent_at": now - timedelta(days=1),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-BENCH-001",
                "target_user_id": "current-read",
                "channel": "email",
                "status": "read",
                "updated_at": now - timedelta(days=2),
                "sent_at": now - timedelta(days=2),
                "read_at": now - timedelta(days=2),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-BENCH-001",
                "target_user_id": "current-failed",
                "channel": "email",
                "status": "failed",
                "updated_at": now - timedelta(days=1),
                "error": "SMTP timeout",
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-BENCH-001",
                "target_user_id": "previous-sent",
                "channel": "email",
                "status": "sent",
                "updated_at": now - timedelta(days=8),
                "sent_at": now - timedelta(days=8),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-BENCH-001",
                "target_user_id": "previous-pending",
                "channel": "email",
                "status": "pending",
                "updated_at": now - timedelta(days=9),
            },
        ]
    )

    response = client.get(
        "/api/v1/admin/communication/delivery/report/benchmarks?days=7&source_kind=notification&scope=system&created_by=creator-benchmark",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    metrics = {item["key"]: item for item in body["metrics"]}
    assert metrics["total_rows"]["current_value"] == 3
    assert metrics["total_rows"]["previous_value"] == 2
    assert metrics["failed_count"]["current_value"] == 1
    assert metrics["failed_count"]["previous_value"] == 0
    assert metrics["read_count"]["current_value"] == 1
    assert metrics["read_count"]["previous_value"] == 0


def test_admin_delivery_incidents_only_return_delivery_alert_routes() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_delivery_incidents@example.com")

    now = datetime.now(timezone.utc)
    fake_db.operational_alert_routes.items.extend(
        [
            {
                "_id": ObjectId(),
                "alert_code": "delivery.failed_rate_spike",
                "level": "critical",
                "message": "Delivery failure spike detected",
                "is_active": True,
                "first_seen_at": now - timedelta(hours=3),
                "last_seen_at": now - timedelta(minutes=10),
                "last_sent_at": now - timedelta(minutes=10),
                "resolved_at": None,
                "last_routing_outcome": "notification_sent",
                "last_routing_outcome_at": now - timedelta(minutes=10),
                "routed_count": 2,
                "resolved_count": 0,
                "cooldown_suppressed_count": 1,
                "notifications_sent_total": 2,
                "history": [
                    {
                        "timestamp": (now - timedelta(hours=3)).isoformat(),
                        "action": "routed",
                        "level": "critical",
                        "message": "Delivery failure spike detected",
                        "notifications_created": 1,
                        "target_user_count": 1,
                    }
                ],
            },
            {
                "_id": ObjectId(),
                "alert_code": "cpu.high",
                "level": "warning",
                "message": "CPU high",
                "is_active": True,
                "first_seen_at": now - timedelta(hours=2),
                "last_seen_at": now - timedelta(minutes=5),
                "history": [],
            },
        ]
    )

    response = client.get(
        "/api/v1/admin/communication/delivery/incidents?limit=25",
        headers=admin_headers,
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 1
    assert body["active_count"] == 1
    assert body["incidents"][0]["alert_code"] == "delivery.failed_rate_spike"
    assert body["incidents"][0]["history"][0]["action"] == "routed"


def test_delivery_anomaly_escalation_routes_with_cooldown_and_resolution() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    _admin_headers(client, "admin_delivery_alerts@example.com")

    now = datetime.now(timezone.utc)
    notification_id = ObjectId()
    fake_db.notifications.items.append(
        {
            "_id": notification_id,
            "public_id": "NTF-ANOM-ROUTE-001",
            "title": "Anomaly Route Notification",
            "message": "Trigger delivery anomaly escalation",
            "scope": "system",
            "created_by": "creator-anomaly-route",
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
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-1",
                "channel": "email",
                "status": "pending",
                "updated_at": now - timedelta(days=2),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-2",
                "channel": "email",
                "status": "pending",
                "updated_at": now - timedelta(days=1),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-2b",
                "channel": "email",
                "status": "pending",
                "updated_at": now - timedelta(days=1),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-3",
                "channel": "email",
                "status": "pending",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-4",
                "channel": "email",
                "status": "pending",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-5",
                "channel": "email",
                "status": "pending",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-6",
                "channel": "email",
                "status": "failed",
                "updated_at": now - timedelta(days=2),
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-7",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-8",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-9",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-ANOM-ROUTE-001",
                "target_user_id": "user-10",
                "channel": "email",
                "status": "failed",
                "updated_at": now,
            },
        ]
    )

    first_run = asyncio.run(background_jobs_service.dispatch_delivery_anomaly_escalations(days=3))
    assert first_run >= 2

    active_alert_notifications = [
        row for row in fake_db.notifications.items if str(row.get("message") or "").startswith("Active system alert [delivery.")
    ]
    assert len(active_alert_notifications) == first_run
    active_routes = {row["alert_code"]: row for row in fake_db.operational_alert_routes.items if row.get("is_active")}
    assert "delivery.failed_rate_spike" in active_routes
    assert "delivery.pending_backlog_rising" in active_routes
    assert fake_db.audit_logs.items[-1]["action_type"] == "communication_delivery_anomaly_escalation"

    second_run = asyncio.run(background_jobs_service.dispatch_delivery_anomaly_escalations(days=3))
    assert second_run == 0
    active_routes_after_cooldown = {row["alert_code"]: row for row in fake_db.operational_alert_routes.items if row.get("is_active")}
    assert active_routes_after_cooldown["delivery.failed_rate_spike"]["cooldown_suppressed_count"] >= 1
    assert active_routes_after_cooldown["delivery.pending_backlog_rising"]["cooldown_suppressed_count"] >= 1

    for row in fake_db.communication_deliveries.items:
        row["status"] = "sent"
        row["error"] = None
        row["updated_at"] = now
        row["sent_at"] = now

    resolved_run = asyncio.run(background_jobs_service.dispatch_delivery_anomaly_escalations(days=3))
    assert resolved_run == len(active_routes_after_cooldown)
    resolved_notifications = [
        row for row in fake_db.notifications.items if str(row.get("message") or "").startswith("Resolved system alert [delivery.")
    ]
    assert len(resolved_notifications) == resolved_run
    assert all(not row.get("is_active") for row in fake_db.operational_alert_routes.items)
    assert fake_db.audit_logs.items[-1]["action_type"] == "communication_delivery_anomaly_escalation"


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


def test_admin_can_retry_failed_notification_email_delivery_for_targeted_user_only() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_notification_retry@example.com")

    first_student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "First Retry Student",
            "email": "student_notification_retry_one@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert first_student.status_code == 201
    second_student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Second Retry Student",
            "email": "student_notification_retry_two@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert second_student.status_code == 201

    first_user = next(item for item in fake_db.users.items if item.get("email") == "student_notification_retry_one@example.com")
    second_user = next(item for item in fake_db.users.items if item.get("email") == "student_notification_retry_two@example.com")

    notification_id = ObjectId()
    now = datetime.now(timezone.utc)
    fake_db.notifications.items.append(
        {
            "_id": notification_id,
            "public_id": "NTF-RETRY-001",
            "title": "Retry Targeted Notification",
            "message": "Retry only one failed notification email row.",
            "scope": "system",
            "priority": "normal",
            "created_by": "admin-retry",
            "created_at": now,
            "is_read": False,
        }
    )
    fake_db.communication_deliveries.items.extend(
        [
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-RETRY-001",
                "target_user_id": str(first_user["_id"]),
                "target_email": first_user["email"],
                "channel": "email",
                "status": "failed",
                "error": "SMTP timeout",
                "updated_at": now,
                "metadata": {"scope": "system"},
            },
            {
                "_id": ObjectId(),
                "source_kind": "notification",
                "source_id": str(notification_id),
                "source_public_id": "NTF-RETRY-001",
                "target_user_id": str(second_user["_id"]),
                "target_email": second_user["email"],
                "channel": "email",
                "status": "failed",
                "error": "SMTP timeout",
                "updated_at": now,
                "metadata": {"scope": "system"},
            },
        ]
    )

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

    original_retry_send = communication_delivery_retry_service.send_outbound_email_batch
    communication_delivery_retry_service.send_outbound_email_batch = successful_send_email_batch
    try:
        retried = client.post(
            f"/api/v1/admin/communication/delivery/notifications/{notification_id}/retry-email",
            json={"target_user_ids": [str(first_user["_id"])], "include_skipped": False},
            headers=admin_headers,
        )
        assert retried.status_code == 200, retried.text
        body = retried.json()
        assert body["retried_count"] == 1
        assert body["details"]["summary"]["email"]["sent_count"] == 1
        assert body["details"]["summary"]["email"]["failed_count"] == 1

        email_rows = [
            row
            for row in fake_db.communication_deliveries.items
            if row.get("source_kind") == "notification" and row.get("channel") == "email"
        ]
        first_row = next(row for row in email_rows if row.get("target_user_id") == str(first_user["_id"]))
        second_row = next(row for row in email_rows if row.get("target_user_id") == str(second_user["_id"]))
        assert first_row["status"] == "sent"
        assert first_row["error"] is None
        assert first_row["sent_at"] is not None
        assert second_row["status"] == "failed"
        assert second_row["error"] == "SMTP timeout"
    finally:
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


def test_student_duplicate_audit_groups_roll_email_and_user_links() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_duplicate_audit@example.com")

    fake_db.students.items.extend(
        [
            {
                "_id": ObjectId(),
                "full_name": "Dup One",
                "roll_number": "DUP-001",
                "email": "dup@example.com",
                "user_id": "student-user-1",
                "class_id": "section-a",
                "is_active": True,
            },
            {
                "_id": ObjectId(),
                "full_name": "Dup Two",
                "roll_number": "DUP-001",
                "email": "dup@example.com",
                "user_id": "student-user-2",
                "class_id": "section-b",
                "is_active": True,
            },
            {
                "_id": ObjectId(),
                "full_name": "Dup Three",
                "roll_number": "DUP-003",
                "email": "unique@example.com",
                "user_id": "student-user-1",
                "class_id": "section-c",
                "is_active": True,
            },
        ]
    )

    response = client.get("/api/v1/students/duplicate-audit", headers=admin_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"]["duplicate_groups"] >= 3
    assert body["summary"]["roll_number_groups"] >= 1
    assert body["summary"]["email_groups"] >= 1
    assert body["summary"]["user_id_groups"] >= 1


def test_grading_policy_updates_transcript_gpa_precision() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    admin_headers = _admin_headers(client, "admin_grading_policy@example.com")

    structure = _seed_canonical_structure(fake_db, suffix="POL1", semester_number=4)
    section = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Policy Section"),
        headers=admin_headers,
    )
    assert section.status_code == 201, section.text

    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Policy Student",
            "email": "policy_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student.status_code == 201
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "policy_student@example.com", "password": "password123"},
    )
    assert student_login.status_code == 200
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Policy Subject", "code": "POL1", "description": "Policy"},
        headers=admin_headers,
    )
    assert subject.status_code == 201, subject.text

    existing_student = next(
        (item for item in fake_db.students.items if item.get("email") == "policy_student@example.com"),
        None,
    )
    existing_student.update(
        {
            "full_name": "Policy Student",
            "roll_number": "POL1-001",
            "email": "policy_student@example.com",
            "user_id": student.json()["id"],
            "class_id": section.json()["id"],
            "is_active": True,
        }
    )
    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": section.json()["id"], "student_id": str(existing_student["_id"])},
        headers=admin_headers,
    )
    assert enrolled.status_code == 201, enrolled.text

    assignment = client.post(
        "/api/v1/assignments/",
        json={
            "title": "Policy Assignment",
            "description": "Desc",
            "subject_id": subject.json()["id"],
            "class_id": section.json()["id"],
            "total_marks": 100,
        },
        headers=admin_headers,
    )
    assert assignment.status_code == 201, assignment.text

    submission = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("policy.txt", b"policy content", "text/plain")},
        headers=student_headers,
    )
    assert submission.status_code == 201, submission.text

    evaluation = client.post(
        "/api/v1/evaluations/",
        json={
            "submission_id": submission.json()["id"],
            "attendance_percent": 90,
            "skill": 2.0,
            "behavior": 2.0,
            "report": 8,
            "viva": 16,
            "final_exam": 48,
            "is_finalized": True,
        },
        headers=admin_headers,
    )
    assert evaluation.status_code == 201, evaluation.text
    released = client.patch(f"/api/v1/evaluations/{evaluation.json()['id']}/release", headers=admin_headers)
    assert released.status_code == 200, released.text

    policy_update = client.patch(
        "/api/v1/evaluations/results/grading-policy",
        json={
            "transcript_precision": 3,
            "grade_points": {"A+": 4.0, "A": 3.6, "B": 3.1, "C": 2.2, "Needs Improvement": 0.0},
        },
        headers=admin_headers,
    )
    assert policy_update.status_code == 200, policy_update.text
    assert policy_update.json()["transcript_precision"] == 3
    assert policy_update.json()["grade_points"]["A"] == 3.6

    published = client.post(
        f"/api/v1/evaluations/results/publish-from-evaluation/{evaluation.json()['id']}",
        headers=admin_headers,
    )
    assert published.status_code == 200, published.text
    assert published.json()["gpa"] == 3.6

    transcript = client.get("/api/v1/evaluations/results/transcript", headers=student_headers)
    assert transcript.status_code == 200, transcript.text
    assert transcript.json()["cgpa"] == 3.6

