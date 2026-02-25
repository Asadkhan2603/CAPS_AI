from fastapi.testclient import TestClient

from app.main import app
from test_auth import _setup_fake_db


def _register_and_login(client: TestClient, *, full_name: str, email: str, role: str, password: str = "password123", extended_roles: list[str] | None = None):
    payload = {
        "full_name": full_name,
        "email": email,
        "password": password,
        "role": role,
    }
    if extended_roles:
        payload["extended_roles"] = extended_roles
    register = client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    return register.json(), {"Authorization": f"Bearer {login.json()['access_token']}"}


def _create_class_stack(client: TestClient, headers: dict, suffix: str):
    course = client.post(
        "/api/v1/courses/",
        json={"name": f"BTECH {suffix}", "code": f"BT{suffix}", "description": "desc"},
        headers=headers,
    )
    assert course.status_code == 201
    year = client.post(
        "/api/v1/years/",
        json={"course_id": course.json()["id"], "year_number": 4, "label": "Fourth Year"},
        headers=headers,
    )
    assert year.status_code == 201
    class_row = client.post(
        "/api/v1/classes/",
        json={"course_id": course.json()["id"], "year_id": year.json()["id"], "name": f"CSE-{suffix}"},
        headers=headers,
    )
    assert class_row.status_code == 201
    return course.json(), year.json(), class_row.json()


def test_timetable_template_must_be_same_class() -> None:
    _setup_fake_db()
    client = TestClient(app)

    _admin, admin_headers = _register_and_login(
        client, full_name="Admin Timetable", email="admin_tt_template@example.com", role="admin"
    )
    teacher, teacher_headers = _register_and_login(
        client,
        full_name="Coordinator Template",
        email="coord_tt_template@example.com",
        role="teacher",
        extended_roles=["class_coordinator"],
    )

    _course_a, _year_a, class_a = _create_class_stack(client, admin_headers, "A1")
    _course_b, _year_b, class_b = _create_class_stack(client, admin_headers, "B1")

    # Force ownership of both classes in fake DB to specifically test same-class template guard.
    client.put(
        f"/api/v1/classes/{class_a['id']}",
        json={"class_coordinator_user_id": teacher["id"]},
        headers=admin_headers,
    )
    client.put(
        f"/api/v1/classes/{class_b['id']}",
        json={"class_coordinator_user_id": teacher["id"]},
        headers=admin_headers,
    )

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Distributed Systems", "code": "CSE401", "description": "desc"},
        headers=admin_headers,
    )
    assert subject.status_code == 201

    base = client.post(
        "/api/v1/timetables/",
        json={
            "class_id": class_a["id"],
            "semester": "SEM-7",
            "shift_id": "shift_1",
            "entries": [
                {
                    "day": "Monday",
                    "slot_key": "p1",
                    "subject_id": subject.json()["id"],
                    "teacher_user_id": teacher["id"],
                    "room_code": "A-101",
                    "session_type": "theory",
                }
            ],
        },
        headers=teacher_headers,
    )
    assert base.status_code == 201

    denied = client.post(
        "/api/v1/timetables/",
        json={
            "class_id": class_b["id"],
            "semester": "SEM-7",
            "shift_id": "shift_1",
            "template_timetable_id": base.json()["id"],
            "entries": [],
        },
        headers=teacher_headers,
    )
    assert denied.status_code == 400
    assert "same class" in denied.json()["detail"].lower()


def test_timetable_subject_teacher_mapping_enforced() -> None:
    _setup_fake_db()
    client = TestClient(app)

    _admin, admin_headers = _register_and_login(
        client, full_name="Admin Timetable 2", email="admin_tt_map@example.com", role="admin"
    )
    teacher_one, teacher_one_headers = _register_and_login(
        client,
        full_name="Coordinator One",
        email="coord_tt_map_one@example.com",
        role="teacher",
        extended_roles=["class_coordinator"],
    )
    teacher_two, _teacher_two_headers = _register_and_login(
        client,
        full_name="Coordinator Two",
        email="coord_tt_map_two@example.com",
        role="teacher",
        extended_roles=["class_coordinator"],
    )

    _course, _year, class_row = _create_class_stack(client, admin_headers, "MAP")
    set_coord = client.put(
        f"/api/v1/classes/{class_row['id']}",
        json={"class_coordinator_user_id": teacher_one["id"]},
        headers=admin_headers,
    )
    assert set_coord.status_code == 200

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Compiler Design", "code": "CSE402", "description": "desc"},
        headers=admin_headers,
    )
    assert subject.status_code == 201

    draft = client.post(
        "/api/v1/timetables/",
        json={
            "class_id": class_row["id"],
            "semester": "SEM-7",
            "shift_id": "shift_1",
            "entries": [
                {
                    "day": "Monday",
                    "slot_key": "p1",
                    "subject_id": subject.json()["id"],
                    "teacher_user_id": teacher_one["id"],
                    "room_code": "LAB-1",
                    "session_type": "practical",
                }
            ],
        },
        headers=teacher_one_headers,
    )
    assert draft.status_code == 201

    denied = client.put(
        f"/api/v1/timetables/{draft.json()['id']}",
        json={
            "entries": [
                {
                    "day": "Monday",
                    "slot_key": "p1",
                    "subject_id": subject.json()["id"],
                    "teacher_user_id": teacher_two["id"],
                    "room_code": "LAB-1",
                    "session_type": "practical",
                }
            ]
        },
        headers=teacher_one_headers,
    )
    assert denied.status_code == 400
    assert "not mapped" in denied.json()["detail"].lower()


def test_student_timetable_skips_inactive_class_enrollment() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    _admin, admin_headers = _register_and_login(
        client, full_name="Admin Timetable 3", email="admin_tt_student@example.com", role="admin"
    )
    teacher, teacher_headers = _register_and_login(
        client,
        full_name="Coordinator Student",
        email="coord_tt_student@example.com",
        role="teacher",
        extended_roles=["class_coordinator"],
    )
    student, student_headers = _register_and_login(
        client,
        full_name="Student Timetable",
        email="student_tt_view@example.com",
        role="student",
    )

    _course_a, _year_a, class_old = _create_class_stack(client, admin_headers, "OLD")
    _course_b, _year_b, class_new = _create_class_stack(client, admin_headers, "NEW")

    client.put(f"/api/v1/classes/{class_old['id']}", json={"class_coordinator_user_id": teacher["id"]}, headers=admin_headers)
    client.put(f"/api/v1/classes/{class_new['id']}", json={"class_coordinator_user_id": teacher["id"]}, headers=admin_headers)

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Cloud Computing", "code": "CSE403", "description": "desc"},
        headers=admin_headers,
    )
    assert subject.status_code == 201

    # Student profile/enrollment setup.
    student_profile = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Student Timetable",
            "roll_number": "EN22CS301037",
            "email": student["email"],
        },
        headers=admin_headers,
    )
    assert student_profile.status_code == 201

    enroll_old = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_old["id"], "student_id": student_profile.json()["id"]},
        headers=admin_headers,
    )
    assert enroll_old.status_code == 201
    enroll_new = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_new["id"], "student_id": student_profile.json()["id"]},
        headers=admin_headers,
    )
    assert enroll_new.status_code == 201

    # Deactivate old class directly in fake db.
    for row in fake_db.classes.items:
        if str(row.get("_id")) == class_old["id"]:
            row["is_active"] = False
            break

    draft = client.post(
        "/api/v1/timetables/",
        json={
            "class_id": class_new["id"],
            "semester": "SEM-7",
            "shift_id": "shift_1",
            "entries": [
                {
                    "day": "Monday",
                    "slot_key": "p1",
                    "subject_id": subject.json()["id"],
                    "teacher_user_id": teacher["id"],
                    "room_code": "B-201",
                    "session_type": "theory",
                }
            ],
        },
        headers=teacher_headers,
    )
    assert draft.status_code == 201

    published = client.post(
        f"/api/v1/timetables/{draft.json()['id']}/publish",
        headers=teacher_headers,
    )
    assert published.status_code == 200

    my_tt = client.get("/api/v1/timetables/my", headers=student_headers)
    assert my_tt.status_code == 200
    assert my_tt.json()["class_id"] == class_new["id"]

