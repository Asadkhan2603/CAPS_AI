from dataclasses import dataclass
from typing import Any, Dict, List

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.endpoints import assignments as assignments_endpoint
from app.api.v1.endpoints import analytics as analytics_endpoint
from app.api.v1.endpoints import audit_logs as audit_logs_endpoint
from app.api.v1.endpoints import auth as auth_endpoint
from app.api.v1.endpoints import classes as classes_endpoint
from app.api.v1.endpoints import courses as courses_endpoint
from app.api.v1.endpoints import evaluations as evaluations_endpoint
from app.api.v1.endpoints import notifications as notifications_endpoint
from app.api.v1.endpoints import section_subjects as section_subjects_endpoint
from app.api.v1.endpoints import sections as sections_endpoint
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
        self.sections = FakeUsersCollection()
        self.section_subjects = FakeUsersCollection()
        self.assignments = FakeUsersCollection()
        self.submissions = FakeUsersCollection()
        self.evaluations = FakeUsersCollection()
        self.similarity_logs = FakeUsersCollection()
        self.notifications = FakeUsersCollection()
        self.audit_logs = FakeUsersCollection()


def _setup_fake_db() -> FakeDB:
    fake_db = FakeDB()
    auth_endpoint.db = fake_db
    users_endpoint.db = fake_db
    courses_endpoint.db = fake_db
    years_endpoint.db = fake_db
    classes_endpoint.db = fake_db
    students_endpoint.db = fake_db
    subjects_endpoint.db = fake_db
    sections_endpoint.db = fake_db
    section_subjects_endpoint.db = fake_db
    assignments_endpoint.db = fake_db
    submissions_endpoint.db = fake_db
    evaluations_endpoint.db = fake_db
    similarity_endpoint.db = fake_db
    analytics_endpoint.db = fake_db
    notifications_endpoint.db = fake_db
    audit_logs_endpoint.db = fake_db
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
            "section_id": "A",
            "is_active": True,
        },
        {
            "_id": ObjectId(),
            "full_name": "Bob",
            "roll_number": "R2",
            "email": "bob@example.com",
            "section_id": "B",
            "is_active": True,
        },
        {
            "_id": ObjectId(),
            "full_name": "Alicia",
            "roll_number": "R3",
            "email": "alicia@example.com",
            "section_id": "A",
            "is_active": False,
        },
    ]

    filtered = client.get(
        "/api/v1/students/?q=ali&section_id=A&skip=0&limit=1",
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
            "section_id": "A",
            "created_by": "teacher1",
            "total_marks": 100,
        },
        {
            "_id": ObjectId(),
            "title": "ML Lab 2",
            "subject_id": "s1",
            "section_id": "B",
            "created_by": "teacher2",
            "total_marks": 100,
        },
        {
            "_id": ObjectId(),
            "title": "OS Assignment",
            "subject_id": "s2",
            "section_id": "A",
            "created_by": "teacher1",
            "total_marks": 100,
        },
    ]

    filtered = client.get(
        "/api/v1/assignments/?q=ML&subject_id=s1&section_id=A&created_by=teacher1&skip=0&limit=1",
        headers=headers,
    )
    assert filtered.status_code == 200
    body = filtered.json()
    assert len(body) == 1
    assert body[0]["title"] == "ML Lab 1"


def test_sections_create_and_filter_for_admin() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin5@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin5@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/sections/",
        json={
            "name": "A",
            "program": "BCA",
            "academic_year": "2026-27",
            "semester": 4,
        },
        headers=headers,
    )
    assert create.status_code == 201

    fake_db.sections.items.append(
        {
            "_id": ObjectId(),
            "name": "B",
            "program": "BSc CS",
            "academic_year": "2025-26",
            "semester": 2,
            "is_active": True,
        }
    )

    listed = client.get(
        "/api/v1/sections/?q=bc&academic_year=2026-27&skip=0&limit=10",
        headers=headers,
    )
    assert listed.status_code == 200
    assert len(listed.json()) == 1


def test_student_cannot_create_section_subject_mapping() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student User",
            "email": "student3@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/v1/auth/login",
        json={"email": "student3@example.com", "password": "password123"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    create = client.post(
        "/api/v1/section-subjects/",
        json={"section_id": "sec1", "subject_id": "sub1", "teacher_user_id": "u1"},
        headers=headers,
    )
    assert create.status_code == 403


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
            "section": "A",
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
        data={"assignment_id": "asg-1", "notes": "first submission"},
        files={"file": ("report.txt", b"my report content", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 201
    assert upload.json()["assignment_id"] == "asg-1"

    listed = client.get("/api/v1/submissions/?assignment_id=asg-1", headers=headers)
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
            "section": "A",
        },
        headers=headers,
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["detail"] == "year_id does not belong to provided course_id"


def test_student_create_requires_valid_section_and_unique_roll_number() -> None:
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

    bad_section = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Student Invalid",
            "roll_number": "R100",
            "email": "invalid@example.com",
            "section_id": str(ObjectId()),
        },
        headers=headers,
    )
    assert bad_section.status_code == 400
    assert bad_section.json()["detail"] == "Section not found for provided section_id"

    section = client.post(
        "/api/v1/sections/",
        json={
            "name": "A",
            "program": "BCA",
            "academic_year": "2026-27",
            "semester": 1,
        },
        headers=headers,
    )
    assert section.status_code == 201

    first = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Student One",
            "roll_number": "R100",
            "email": "s1@example.com",
            "section_id": section.json()["id"],
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
            "section_id": section.json()["id"],
        },
        headers=headers,
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Roll number already exists"


def test_section_subject_create_validates_section_subject_and_teacher() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin_mapping_validate@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin_register.status_code == 201
    teacher_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher User",
            "email": "teacher_mapping_validate@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert teacher_register.status_code == 201
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_mapping_validate@example.com", "password": "password123"},
    )
    headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    section = client.post(
        "/api/v1/sections/",
        json={
            "name": "A",
            "program": "BCA",
            "academic_year": "2026-27",
            "semester": 3,
        },
        headers=headers,
    )
    assert section.status_code == 201
    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Data Mining", "code": "DM101", "description": "DM"},
        headers=headers,
    )
    assert subject.status_code == 201

    missing_subject = client.post(
        "/api/v1/section-subjects/",
        json={
            "section_id": section.json()["id"],
            "subject_id": str(ObjectId()),
            "teacher_user_id": teacher_register.json()["id"],
        },
        headers=headers,
    )
    assert missing_subject.status_code == 400
    assert missing_subject.json()["detail"] == "Subject not found for provided subject_id"

    non_teacher = client.post(
        "/api/v1/section-subjects/",
        json={
            "section_id": section.json()["id"],
            "subject_id": subject.json()["id"],
            "teacher_user_id": admin_register.json()["id"],
        },
        headers=headers,
    )
    assert non_teacher.status_code == 400
    assert non_teacher.json()["detail"] == "teacher_user_id must belong to a teacher role"
