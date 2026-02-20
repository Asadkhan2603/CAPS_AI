from dataclasses import dataclass
from typing import Any, Dict, List

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints import assignments as assignments_endpoint
from app.api.v1.endpoints import analytics as analytics_endpoint
from app.api.v1.endpoints import audit_logs as audit_logs_endpoint
from app.api.v1.endpoints import club_events as club_events_endpoint
from app.api.v1.endpoints import clubs as clubs_endpoint
from app.api.v1.endpoints import enrollments as enrollments_endpoint
from app.api.v1.endpoints import event_registrations as event_registrations_endpoint
from app.api.v1.endpoints import auth as auth_endpoint
from app.api.v1.endpoints import classes as classes_endpoint
from app.api.v1.endpoints import courses as courses_endpoint
from app.api.v1.endpoints import evaluations as evaluations_endpoint
from app.api.v1.endpoints import notices as notices_endpoint
from app.api.v1.endpoints import notifications as notifications_endpoint
from app.api.v1.endpoints import review_tickets as review_tickets_endpoint
from app.api.v1.endpoints import similarity as similarity_endpoint
from app.api.v1.endpoints import students as students_endpoint
from app.api.v1.endpoints import submissions as submissions_endpoint
from app.api.v1.endpoints import subjects as subjects_endpoint
from app.api.v1.endpoints import users as users_endpoint
from app.api.v1.endpoints import years as years_endpoint
from app.core import security as security_core
from app.services import audit as audit_service
from app.services import notifications as notifications_service


@dataclass
class InsertOneResult:
    inserted_id: ObjectId


class FakeCursor:
    def __init__(self, items: List[Dict[str, Any]]) -> None:
        self.items = items
        self._skip = 0
        self._limit: int | None = None

    async def to_list(self, length: int = 1000) -> List[Dict[str, Any]]:
        start = self._skip
        end = start + self._limit if self._limit is not None else None
        scoped = self.items[start:end]
        return scoped[:length]

    def skip(self, amount: int) -> "FakeCursor":
        self._skip = max(0, amount)
        return self

    def limit(self, amount: int) -> "FakeCursor":
        self._limit = max(0, amount)
        return self


class FakeUsersCollection:
    def __init__(self) -> None:
        self.items: List[Dict[str, Any]] = []

    async def find_one(self, query: Dict[str, Any]) -> Dict[str, Any] | None:
        for item in self.items:
            if _matches_query(item, query):
                return item
        return None

    async def create_index(self, key: str, unique: bool = False) -> None:
        _ = (key, unique)

    async def insert_one(self, document: Dict[str, Any]) -> InsertOneResult:
        if "email" in document and document["email"] is not None:
            for item in self.items:
                if item.get("email") == document["email"]:
                    raise Exception("duplicate key")
        inserted_id = ObjectId()
        saved = {**document, "_id": inserted_id}
        self.items.append(saved)
        return InsertOneResult(inserted_id=inserted_id)

    def find(self, query: Dict[str, Any]) -> FakeCursor:
        return FakeCursor([item for item in self.items if _matches_query(item, query)])

    async def count_documents(self, query: Dict[str, Any]) -> int:
        return len([item for item in self.items if _matches_query(item, query)])

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any]):
        matched = 0
        for item in self.items:
            if _matches_query(item, query):
                matched += 1
                item.update(update.get("$set", {}))
                break
        return type("UpdateResult", (), {"matched_count": matched})()

    async def delete_one(self, query: Dict[str, Any]):
        deleted = 0
        for index, item in enumerate(self.items):
            if _matches_query(item, query):
                self.items.pop(index)
                deleted = 1
                break
        return type("DeleteResult", (), {"deleted_count": deleted})()


def _matches_query(item: Dict[str, Any], query: Dict[str, Any]) -> bool:
    if not query:
        return True
    for key, value in query.items():
        if key == "$or":
            if not any(_matches_query(item, subquery) for subquery in value):
                return False
            continue
        if isinstance(value, dict) and "$regex" in value:
            pattern = str(value["$regex"]).lower()
            field_val = str(item.get(key, "")).lower()
            if pattern not in field_val:
                return False
            continue
        if isinstance(value, dict) and "$in" in value:
            allowed_values = value["$in"]
            item_val = item.get(key)
            if isinstance(item_val, list):
                if not any(v in item_val for v in allowed_values):
                    return False
            else:
                if item_val not in allowed_values:
                    return False
            continue
        if item.get(key) != value:
            return False
    return True


class FakeDB:
    def __init__(self) -> None:
        self.users = FakeUsersCollection()
        self.courses = FakeUsersCollection()
        self.years = FakeUsersCollection()
        self.classes = FakeUsersCollection()
        self.students = FakeUsersCollection()
        self.subjects = FakeUsersCollection()
        self.assignments = FakeUsersCollection()
        self.submissions = FakeUsersCollection()
        self.evaluations = FakeUsersCollection()
        self.similarity_logs = FakeUsersCollection()
        self.notifications = FakeUsersCollection()
        self.notices = FakeUsersCollection()
        self.clubs = FakeUsersCollection()
        self.club_events = FakeUsersCollection()
        self.event_registrations = FakeUsersCollection()
        self.audit_logs = FakeUsersCollection()
        self.enrollments = FakeUsersCollection()
        self.review_tickets = FakeUsersCollection()


def _setup_fake_db() -> FakeDB:
    fake_db = FakeDB()
    auth_endpoint.db = fake_db
    users_endpoint.db = fake_db
    courses_endpoint.db = fake_db
    years_endpoint.db = fake_db
    classes_endpoint.db = fake_db
    students_endpoint.db = fake_db
    subjects_endpoint.db = fake_db
    assignments_endpoint.db = fake_db
    submissions_endpoint.db = fake_db
    evaluations_endpoint.db = fake_db
    similarity_endpoint.db = fake_db
    analytics_endpoint.db = fake_db
    notifications_endpoint.db = fake_db
    notices_endpoint.db = fake_db
    clubs_endpoint.db = fake_db
    club_events_endpoint.db = fake_db
    event_registrations_endpoint.db = fake_db
    review_tickets_endpoint.db = fake_db
    audit_logs_endpoint.db = fake_db
    enrollments_endpoint.db = fake_db
    notifications_service.db = fake_db
    audit_service.db = fake_db
    security_core.db = fake_db
    return fake_db


def test_register_login_me_and_admin_users_flow() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201
    assert register.json()["email"] == "admin@example.com"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert token

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"

    users = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200
    assert len(users.json()) == 1


def test_student_cannot_access_users_endpoint() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    users = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 403


def test_student_cannot_access_students_endpoint() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student2@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student2@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    students = client.get(
        "/api/v1/students/",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert students.status_code == 403


def test_students_list_supports_pagination_and_filters() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin2@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin_register.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin2@example.com", "password": "password123"},
    )
    token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_db.students.items = [
        {
            "_id": ObjectId(),
            "full_name": "Alice",
            "roll_number": "R1",
            "email": "alice@example.com",
            "class_id": "A",
            "is_active": True,
        },
        {
            "_id": ObjectId(),
            "full_name": "Bob",
            "roll_number": "R2",
            "email": "bob@example.com",
            "class_id": "B",
            "is_active": True,
        },
        {
            "_id": ObjectId(),
            "full_name": "Alicia",
            "roll_number": "R3",
            "email": "alicia@example.com",
            "class_id": "A",
            "is_active": False,
        },
    ]

    filtered = client.get(
        "/api/v1/students/?q=ali&class_id=A&skip=0&limit=1",
        headers=headers,
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert len(body) == 1
    assert body[0]["full_name"] == "Alice"


def test_subjects_list_supports_pagination_and_filters() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin3@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin_register.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin3@example.com", "password": "password123"},
    )
    token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_db.subjects.items = [
        {
            "_id": ObjectId(),
            "name": "Machine Learning",
            "code": "ML101",
            "description": "Intro",
            "is_active": True,
        },
        {
            "_id": ObjectId(),
            "name": "Operating Systems",
            "code": "CS205",
            "description": "Core",
            "is_active": True,
        },
        {
            "_id": ObjectId(),
            "name": "Advanced ML",
            "code": "ML501",
            "description": "Advanced",
            "is_active": False,
        },
    ]

    filtered = client.get(
        "/api/v1/subjects/?q=ml&is_active=true&skip=0&limit=5",
        headers=headers,
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert len(body) == 1
    assert body[0]["code"] == "ML101"


def test_assignments_list_supports_pagination_and_filters() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin4@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin_register.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin4@example.com", "password": "password123"},
    )
    token = admin_login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    fake_db.assignments.items = [
        {
            "_id": ObjectId(),
            "title": "ML Lab 1",
            "subject_id": "s1",
            "class_id": "A",
            "created_by": "teacher1",
            "total_marks": 100,
        },
        {
            "_id": ObjectId(),
            "title": "ML Lab 2",
            "subject_id": "s1",
            "class_id": "B",
            "created_by": "teacher2",
            "total_marks": 100,
        },
        {
            "_id": ObjectId(),
            "title": "OS Assignment",
            "subject_id": "s2",
            "class_id": "A",
            "created_by": "teacher1",
            "total_marks": 100,
        },
    ]

    filtered = client.get(
        "/api/v1/assignments/?q=ML&subject_id=s1&class_id=A&created_by=teacher1&skip=0&limit=1",
        headers=headers,
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert len(body) == 1
    assert body[0]["title"] == "ML Lab 1"


def test_teacher_can_have_extended_roles() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Year Head Teacher",
            "email": "teacher_role@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["year_head", "class_coordinator"],
        },
    )
    assert register.status_code == 201
    assert register.json()["extended_roles"] == ["year_head", "class_coordinator"]


def test_non_teacher_cannot_have_extended_roles() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin_roles@example.com",
            "password": "password123",
            "role": "admin",
            "extended_roles": ["year_head"],
        },
    )
    assert register.status_code == 400


def test_admin_can_create_courses_years_and_classes() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin6@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin6@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    course = client.post(
        "/api/v1/courses/",
        json={"name": "BCA", "code": "BCA", "description": "Bachelor course"},
        headers=headers,
    )
    assert course.status_code == 201
    course_id = course.json()["id"]

    year = client.post(
        "/api/v1/years/",
        json={"course_id": course_id, "year_number": 1, "label": "First Year"},
        headers=headers,
    )
    assert year.status_code == 201
    year_id = year.json()["id"]

    class_item = client.post(
        "/api/v1/classes/",
        json={
            "course_id": course_id,
            "year_id": year_id,
            "name": "BCA FY",
        },
        headers=headers,
    )
    assert class_item.status_code == 201


def test_student_cannot_create_course() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student User",
            "email": "student4@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student4@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    course = client.post(
        "/api/v1/courses/",
        json={"name": "MCA", "code": "MCA", "description": "Master course"},
        headers=headers,
    )
    assert course.status_code == 403


def test_student_can_upload_and_list_own_submissions() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin Maker",
            "email": "admin_upload_setup@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin_register.status_code == 201
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_upload_setup@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Submission Assignment", "description": "desc", "total_marks": 100},
        headers=admin_headers,
    )
    assert assignment.status_code == 201

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Submitter",
            "email": "student_upload@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_upload@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"], "notes": "first submission"},
        files={"file": ("report.txt", b"my report content", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 201
    assert upload.json()["assignment_id"] == assignment.json()["id"]

    listed = client.get(f"/api/v1/submissions/?assignment_id={assignment.json()['id']}", headers=headers)
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_student_cannot_view_others_submission() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    first = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_owner@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_other@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert second.status_code == 201

    second_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_other@example.com", "password": "password123"},
    )
    second_token = second_login.json()["access_token"]
    second_headers = {"Authorization": f"Bearer {second_token}"}

    fake_db.submissions.items = [
        {
            "_id": ObjectId(),
            "assignment_id": "asg-2",
            "student_user_id": first.json()["id"],
            "original_filename": "doc.txt",
            "stored_filename": "stored.txt",
            "file_size_bytes": 10,
            "status": "submitted",
        }
    ]

    submission_id = str(fake_db.submissions.items[0]["_id"])
    response = client.get(f"/api/v1/submissions/{submission_id}", headers=second_headers)
    assert response.status_code == 403


def test_year_create_requires_valid_course_id() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin_year_validate@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_year_validate@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    create = client.post(
        "/api/v1/years/",
        json={"course_id": str(ObjectId()), "year_number": 1, "label": "First Year"},
        headers=headers,
    )
    assert create.status_code == 400
    assert create.json()["detail"] == "Course not found for provided course_id"


def test_course_and_subject_code_must_be_unique() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin_unique_codes@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_unique_codes@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    first_course = client.post(
        "/api/v1/courses/",
        json={"name": "Course A", "code": "CSE101", "description": "A"},
        headers=headers,
    )
    assert first_course.status_code == 201
    duplicate_course = client.post(
        "/api/v1/courses/",
        json={"name": "Course B", "code": "cse101", "description": "B"},
        headers=headers,
    )
    assert duplicate_course.status_code == 400
    assert duplicate_course.json()["detail"] == "Course code already exists"

    first_subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Subject A", "code": "ML101", "description": "A"},
        headers=headers,
    )
    assert first_subject.status_code == 201
    duplicate_subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Subject B", "code": "ml101", "description": "B"},
        headers=headers,
    )
    assert duplicate_subject.status_code == 400
    assert duplicate_subject.json()["detail"] == "Subject code already exists"


def test_class_create_requires_matching_course_and_year() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin_class_validate@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_class_validate@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    course_one = client.post(
        "/api/v1/courses/",
        json={"name": "Course One", "code": "CO1", "description": "One"},
        headers=headers,
    )
    assert course_one.status_code == 201
    course_two = client.post(
        "/api/v1/courses/",
        json={"name": "Course Two", "code": "CO2", "description": "Two"},
        headers=headers,
    )
    assert course_two.status_code == 201

    year = client.post(
        "/api/v1/years/",
        json={"course_id": course_one.json()["id"], "year_number": 1, "label": "FY"},
        headers=headers,
    )
    assert year.status_code == 201

    mismatch = client.post(
        "/api/v1/classes/",
        json={
            "course_id": course_two.json()["id"],
            "year_id": year.json()["id"],
            "name": "Invalid Class",
        },
        headers=headers,
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["detail"] == "year_id does not belong to provided course_id"


def test_student_create_requires_valid_class_and_unique_roll_number() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin_student_validate@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_student_validate@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    bad_class = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Student Invalid",
            "roll_number": "R100",
            "email": "invalid@example.com",
            "class_id": str(ObjectId()),
        },
        headers=headers,
    )
    assert bad_class.status_code == 400
    assert bad_class.json()["detail"] == "Class not found for provided class_id"

    course = client.post(
        "/api/v1/courses/",
        json={"name": "BCA", "code": "BCA01", "description": "Course"},
        headers=headers,
    )
    assert course.status_code == 201
    year = client.post(
        "/api/v1/years/",
        json={"course_id": course.json()["id"], "year_number": 1, "label": "Year 1"},
        headers=headers,
    )
    assert year.status_code == 201
    class_item = client.post(
        "/api/v1/classes/",
        json={"course_id": course.json()["id"], "year_id": year.json()["id"], "name": "BCA Y1"},
        headers=headers,
    )
    assert class_item.status_code == 201

    first = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Student One",
            "roll_number": "R100",
            "email": "s1@example.com",
            "class_id": class_item.json()["id"],
        },
        headers=headers,
    )
    assert first.status_code == 201
    duplicate = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Student Two",
            "roll_number": "R100",
            "email": "s2@example.com",
            "class_id": class_item.json()["id"],
        },
        headers=headers,
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Roll number already exists"


def test_admin_can_assign_teacher_extension_roles() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_extensions_flow@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher",
            "email": "teacher_extensions_flow@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert admin.status_code == 201
    assert teacher.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_extensions_flow@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    update = client.patch(
        f"/api/v1/users/{teacher.json()['id']}/extensions",
        json={"extended_roles": ["year_head", "class_coordinator"]},
        headers=headers,
    )
    assert update.status_code == 200
    assert update.json()["extended_roles"] == ["year_head", "class_coordinator"]


def test_class_coordinator_enrollment_permissions_enforced() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_enroll_flow@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    teacher_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator One",
            "email": "coordinator_one@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    teacher_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator Two",
            "email": "coordinator_two@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    assert admin.status_code == 201
    assert teacher_one.status_code == 201
    assert teacher_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_enroll_flow@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    course = client.post(
        "/api/v1/courses/",
        json={"name": "BTech", "code": "BT1", "description": "desc"},
        headers=admin_headers,
    )
    year = client.post(
        "/api/v1/years/",
        json={"course_id": course.json()["id"], "year_number": 1, "label": "FY"},
        headers=admin_headers,
    )
    class_one = client.post(
        "/api/v1/classes/",
        json={
            "course_id": course.json()["id"],
            "year_id": year.json()["id"],
            "name": "Class One",
            "class_coordinator_user_id": teacher_one.json()["id"],
        },
        headers=admin_headers,
    )
    class_two = client.post(
        "/api/v1/classes/",
        json={
            "course_id": course.json()["id"],
            "year_id": year.json()["id"],
            "name": "Class Two",
            "class_coordinator_user_id": teacher_two.json()["id"],
        },
        headers=admin_headers,
    )
    student = client.post(
        "/api/v1/students/",
        json={"full_name": "Student A", "roll_number": "E100", "email": "stud_e100@example.com"},
        headers=admin_headers,
    )
    assert class_one.status_code == 201
    assert class_two.status_code == 201
    assert student.status_code == 201

    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coordinator_one@example.com", "password": "password123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}

    denied = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_two.json()["id"], "student_id": student.json()["id"]},
        headers=teacher_headers,
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not allowed to manage this class"

    allowed = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_one.json()["id"], "student_id": student.json()["id"]},
        headers=teacher_headers,
    )
    assert allowed.status_code == 201
    assert allowed.json()["class_id"] == class_one.json()["id"]


def test_year_head_can_enroll_students_across_classes() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_yearhead_enroll@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    year_head = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Year Head",
            "email": "yearhead@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["year_head"],
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Class Coordinator",
            "email": "classcoord@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    assert admin.status_code == 201
    assert year_head.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_yearhead_enroll@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    course = client.post(
        "/api/v1/courses/",
        json={"name": "BSc", "code": "BSC1", "description": "desc"},
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
            "name": "General Class",
            "class_coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    student = client.post(
        "/api/v1/students/",
        json={"full_name": "Student B", "roll_number": "E101", "email": "stud_e101@example.com"},
        headers=admin_headers,
    )
    assert class_item.status_code == 201
    assert student.status_code == 201

    year_head_login = client.post(
        "/api/v1/auth/login",
        json={"email": "yearhead@example.com", "password": "password123"},
    )
    year_head_headers = {"Authorization": f"Bearer {year_head_login.json()['access_token']}"}

    enrolled = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_item.json()["id"], "student_id": student.json()["id"]},
        headers=year_head_headers,
    )
    assert enrolled.status_code == 201


def test_student_cannot_upload_when_assignment_closed() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_closed_assignment@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student",
            "email": "student_closed_assignment@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin_register.status_code == 201
    assert student_register.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_closed_assignment@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Closed A", "description": "desc", "total_marks": 100, "status": "closed"},
        headers=admin_headers,
    )
    assert assignment.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_closed_assignment@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("report.txt", b"submission body", "text/plain")},
        headers=student_headers,
    )
    assert upload.status_code == 400
    assert upload.json()["detail"] == "Assignment is closed"


def test_teacher_cannot_access_out_of_scope_submission() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_scope_submission@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    teacher_owner = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner Teacher",
            "email": "owner_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    teacher_other = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other Teacher",
            "email": "other_teacher@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student C",
            "email": "student_scope_submission@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert teacher_owner.status_code == 201
    assert teacher_other.status_code == 201
    assert student.status_code == 201

    owner_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner_teacher@example.com", "password": "password123"},
    )
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Owner Assignment", "description": "desc", "total_marks": 100},
        headers=owner_headers,
    )
    assert assignment.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_scope_submission@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("report.txt", b"scope body", "text/plain")},
        headers=student_headers,
    )
    assert upload.status_code == 201
    submission_id = upload.json()["id"]

    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": "other_teacher@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    denied = client.get(f"/api/v1/submissions/{submission_id}", headers=other_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not allowed to view this submission"

    ai_denied = client.post(f"/api/v1/submissions/{submission_id}/ai-evaluate", headers=other_headers)
    assert ai_denied.status_code == 403
    assert ai_denied.json()["detail"] == "Not allowed to evaluate this submission"


def test_second_admin_registration_is_blocked() -> None:
    _setup_fake_db()
    client = TestClient(app)

    first_admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin One",
            "email": "admin_one@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert first_admin.status_code == 201

    second_admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin Two",
            "email": "admin_two@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert second_admin.status_code == 403
    assert second_admin.json()["detail"] == "Admin account registration is closed"


def test_student_cannot_tamper_submission_ai_fields() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_submission_tamper@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student",
            "email": "student_submission_tamper@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_submission_tamper@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    assignment = client.post(
        "/api/v1/assignments/",
        json={"title": "Secure Assignment", "description": "desc", "total_marks": 100},
        headers=admin_headers,
    )
    assert assignment.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_submission_tamper@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment.json()["id"]},
        files={"file": ("report.txt", b"submission body", "text/plain")},
        headers=student_headers,
    )
    assert upload.status_code == 201
    submission_id = upload.json()["id"]

    tamper = client.put(
        f"/api/v1/submissions/{submission_id}",
        json={"notes": "updated note", "ai_score": 10, "ai_feedback": "forged"},
        headers=student_headers,
    )
    assert tamper.status_code == 200
    assert tamper.json()["notes"] == "updated note"
    assert tamper.json()["ai_score"] is None
    assert tamper.json()["ai_feedback"] is None


def test_class_coordinator_cannot_list_other_class_enrollments() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_enrollment_scope@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator One",
            "email": "coord_one_enrollment_scope@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    coordinator_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator Two",
            "email": "coord_two_enrollment_scope@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student",
            "email": "student_enrollment_scope@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator_one.status_code == 201
    assert coordinator_two.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_enrollment_scope@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    course = client.post(
        "/api/v1/courses/",
        json={"name": "BCA", "code": "BCA2", "description": "desc"},
        headers=admin_headers,
    )
    year = client.post(
        "/api/v1/years/",
        json={"course_id": course.json()["id"], "year_number": 1, "label": "FY"},
        headers=admin_headers,
    )
    class_one = client.post(
        "/api/v1/classes/",
        json={
            "course_id": course.json()["id"],
            "year_id": year.json()["id"],
            "name": "Class One",
            "class_coordinator_user_id": coordinator_one.json()["id"],
        },
        headers=admin_headers,
    )
    class_two = client.post(
        "/api/v1/classes/",
        json={
            "course_id": course.json()["id"],
            "year_id": year.json()["id"],
            "name": "Class Two",
            "class_coordinator_user_id": coordinator_two.json()["id"],
        },
        headers=admin_headers,
    )
    student_doc = client.post(
        "/api/v1/students/",
        json={"full_name": "Student A", "roll_number": "E302", "email": "student_a_e302@example.com"},
        headers=admin_headers,
    )
    assert class_one.status_code == 201
    assert class_two.status_code == 201
    assert student_doc.status_code == 201

    enroll_one = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_one.json()["id"], "student_id": student_doc.json()["id"]},
        headers=admin_headers,
    )
    enroll_two = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_two.json()["id"], "student_id": student_doc.json()["id"]},
        headers=admin_headers,
    )
    assert enroll_one.status_code == 201
    assert enroll_two.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_one_enrollment_scope@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    listed = client.get("/api/v1/enrollments/", headers=coordinator_headers)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["class_id"] == class_one.json()["id"]


def test_students_only_receive_college_scope_notices() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_notice_scope@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student",
            "email": "student_notice_scope@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_notice_scope@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    college_notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "Campus Update",
            "message": "General announcement",
            "priority": "normal",
            "scope": "college",
        },
        headers=admin_headers,
    )
    class_notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "Class Internal",
            "message": "Class-only announcement",
            "priority": "normal",
            "scope": "class",
            "scope_ref_id": "class-1",
        },
        headers=admin_headers,
    )
    assert college_notice.status_code == 201
    assert class_notice.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_notice_scope@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    listed = client.get("/api/v1/notices/", headers=student_headers)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["scope"] == "college"


def test_club_coordinator_can_view_own_event_registrations() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_regs@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Club Coordinator",
            "email": "club_coord_regs@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["club_coordinator"],
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Registrant",
            "email": "student_regs@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_regs@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Robotics Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "club_coord_regs@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Demo Day", "capacity": 50},
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_regs@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert registration.status_code == 201

    listed = client.get(
        f"/api/v1/event-registrations/?event_id={event.json()['id']}",
        headers=coordinator_headers,
    )
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["student_user_id"] == student.json()["id"]
    assert body[0]["student_name"] == "Student Registrant"
    assert body[0]["student_email"] == "student_regs@example.com"


def test_teacher_cannot_view_other_club_event_registrations() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_regs_denied@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    owner = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner Coordinator",
            "email": "owner_coord_regs@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["club_coordinator"],
        },
    )
    other_teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other Teacher",
            "email": "other_teacher_regs@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["club_coordinator"],
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Registrant 2",
            "email": "student_regs_2@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert owner.status_code == 201
    assert other_teacher.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_regs_denied@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Music Club",
            "description": "Club",
            "coordinator_user_id": owner.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    owner_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner_coord_regs@example.com", "password": "password123"},
    )
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Music Fest", "capacity": 25},
        headers=owner_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_regs_2@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert registration.status_code == 201

    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": "other_teacher_regs@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    denied = client.get(
        f"/api/v1/event-registrations/?event_id={event.json()['id']}",
        headers=other_headers,
    )
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not allowed to view registrations for this event"


def test_student_can_submit_event_registration_profile_details() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_event_profile@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Profile",
            "email": "student_event_profile@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_event_profile@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Drama Club", "description": "Club"},
        headers=admin_headers,
    )
    assert club.status_code == 201

    event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Audition Day", "capacity": 20},
        headers=admin_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_event_profile@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/submit",
        data={
            "event_id": event.json()["id"],
            "enrollment_number": "ENR-1001",
            "full_name": "Student Profile",
            "email": "student_event_profile@example.com",
            "year": "2nd Year",
            "course_branch": "B.Tech CSE",
            "class_name": "B.Tech CSE Y2-A",
            "phone_number": "9999999999",
            "whatsapp_number": "9999999999",
            "payment_qr_code": "UPI-REF-12345",
        },
        headers=student_headers,
    )
    assert registration.status_code == 201
    body = registration.json()
    assert body["event_id"] == event.json()["id"]
    assert body["enrollment_number"] == "ENR-1001"
    assert body["course_branch"] == "B.Tech CSE"
    assert body["payment_qr_code"] == "UPI-REF-12345"


def test_admin_can_delete_club_event_but_teacher_cannot() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_delete_event@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher",
            "email": "teacher_delete_event@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["club_coordinator"],
        },
    )
    assert admin.status_code == 201
    assert teacher.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_delete_event@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Delete Event Club", "description": "Club", "coordinator_user_id": teacher.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Delete Event", "capacity": 10},
        headers=admin_headers,
    )
    assert event.status_code == 201
    event_id = event.json()["id"]

    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_delete_event@example.com", "password": "password123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}
    teacher_delete = client.delete(f"/api/v1/club-events/{event_id}", headers=teacher_headers)
    assert teacher_delete.status_code == 403

    admin_delete = client.delete(f"/api/v1/club-events/{event_id}", headers=admin_headers)
    assert admin_delete.status_code == 200
    assert admin_delete.json()["message"] == "Club event deleted"


def test_club_coordinator_can_archive_club_event() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_archive_event@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_archive_event@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["club_coordinator"],
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_archive_event@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Archive Club", "description": "Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_archive_event@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}

    event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Archive Event", "capacity": 25},
        headers=coordinator_headers,
    )
    assert event.status_code == 201
    event_id = event.json()["id"]

    archived = client.put(
        f"/api/v1/club-events/{event_id}",
        json={"status": "archived"},
        headers=coordinator_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["status"] == "archived"


def test_teacher_without_coordinator_classes_gets_empty_academic_structure() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_structure_scope@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    teacher_owner = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner Teacher",
            "email": "owner_structure_scope@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    teacher_other = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other Teacher",
            "email": "other_structure_scope@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert admin.status_code == 201
    assert teacher_owner.status_code == 201
    assert teacher_other.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_structure_scope@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    course = client.post(
        "/api/v1/courses/",
        json={"name": "BTech", "code": "BTSC", "description": "desc"},
        headers=admin_headers,
    )
    year = client.post(
        "/api/v1/years/",
        json={"course_id": course.json()["id"], "year_number": 2, "label": "2nd Year"},
        headers=admin_headers,
    )
    class_item = client.post(
        "/api/v1/classes/",
        json={
            "course_id": course.json()["id"],
            "year_id": year.json()["id"],
            "name": "Computer Science Engineering",
            "faculty_name": "Faculty of Engineering",
            "branch_name": "Computer Science Engineering",
            "class_coordinator_user_id": teacher_owner.json()["id"],
        },
        headers=admin_headers,
    )
    assert class_item.status_code == 201

    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": "other_structure_scope@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    structure = client.get("/api/v1/analytics/academic-structure", headers=other_headers)
    assert structure.status_code == 200
    assert structure.json()["courses"] == []


def test_user_cannot_access_other_user_avatar() -> None:
    _setup_fake_db()
    client = TestClient(app)

    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_avatar_one@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_avatar_two@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_avatar_one@example.com", "password": "password123"},
    )
    one_headers = {"Authorization": f"Bearer {one_login.json()['access_token']}"}
    upload = client.post(
        "/api/v1/auth/profile/avatar",
        files={"file": ("avatar.png", b"fakepngcontent", "image/png")},
        headers=one_headers,
    )
    assert upload.status_code == 200
    target_user_id = upload.json()["id"]

    two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_avatar_two@example.com", "password": "password123"},
    )
    two_headers = {"Authorization": f"Bearer {two_login.json()['access_token']}"}
    denied = client.get(f"/api/v1/auth/profile/avatar/{target_user_id}", headers=two_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not allowed to view this avatar"

