from types import SimpleNamespace

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.core import security as security_core
from app.core.permission_registry import ACADEMIC_ROUTE_PERMISSION_MATRIX
from app.api.v1.endpoints import classes as classes_endpoint
from app.api.v1.endpoints import courses as courses_endpoint
from app.api.v1.endpoints import faculties as faculties_endpoint
from app.api.v1.endpoints import programs as programs_endpoint


class _InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _SimpleCollection:
    def __init__(self, items=None):
        self.items = list(items or [])

    async def find_one(self, query):
        for item in self.items:
            matched = True
            for key, value in query.items():
                if item.get(key) != value:
                    matched = False
                    break
            if matched:
                return item
        return None

    async def insert_one(self, document):
        inserted_id = ObjectId()
        saved = {**document, "_id": inserted_id}
        self.items.append(saved)
        return _InsertResult(inserted_id)


def _override_user(user):
    async def _dependency_override():
        return user

    return _dependency_override


def test_academic_route_permission_matrix_tracks_canonical_write_permissions() -> None:
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/faculties"]["POST"] == "faculties.manage"
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/programs"]["POST"] == "programs.manage"
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/sections"]["DELETE"] == "sections.manage"
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/courses"]["POST"] == "courses.manage (legacy module)"
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/years"]["POST"] == "years.manage (legacy module)"
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/branches"]["POST"] == "branches.manage (legacy module)"


def test_permission_registry_grants_expected_admin_type_access() -> None:
    department_admin = {"role": "admin", "admin_type": "department_admin", "extended_roles": []}
    academic_admin = {"role": "admin", "admin_type": "academic_admin", "extended_roles": []}
    teacher = {"role": "teacher", "extended_roles": []}

    assert security_core.has_permission(department_admin, "programs.manage") is True
    assert security_core.has_permission(department_admin, "sections.manage") is True
    assert security_core.has_permission(department_admin, "faculties.manage") is False
    assert security_core.has_permission(department_admin, "courses.manage") is False
    assert security_core.has_permission(academic_admin, "faculties.manage") is True
    assert security_core.has_permission(teacher, "programs.manage") is False


def test_department_admin_cannot_create_faculty() -> None:
    client = TestClient(app)
    app.dependency_overrides[security_core.get_current_user] = _override_user(
        {"_id": str(ObjectId()), "role": "admin", "admin_type": "department_admin", "extended_roles": []}
    )
    try:
        response = client.post(
            "/api/v1/faculties/",
            json={"name": "Faculty of Engineering", "code": "FOENG"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing required permission: faculties.manage"


def test_academic_admin_can_create_faculty() -> None:
    client = TestClient(app)
    original_db = faculties_endpoint.db
    faculties_endpoint.db = SimpleNamespace(faculties=_SimpleCollection())
    app.dependency_overrides[security_core.get_current_user] = _override_user(
        {"_id": str(ObjectId()), "role": "admin", "admin_type": "academic_admin", "extended_roles": []}
    )
    try:
        response = client.post(
            "/api/v1/faculties/",
            json={"name": "Faculty of Engineering", "code": "FOENG"},
        )
    finally:
        faculties_endpoint.db = original_db
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["code"] == "FOENG"


def test_department_admin_can_create_program() -> None:
    client = TestClient(app)
    department_id = ObjectId()
    departments = _SimpleCollection([{"_id": department_id, "name": "Computer Science", "code": "FOENG-D03"}])
    programs = _SimpleCollection()
    original_db = programs_endpoint.db
    programs_endpoint.db = SimpleNamespace(
        departments=departments,
        programs=programs,
    )
    app.dependency_overrides[security_core.get_current_user] = _override_user(
        {"_id": str(ObjectId()), "role": "admin", "admin_type": "department_admin", "extended_roles": []}
    )
    try:
        response = client.post(
            "/api/v1/programs/",
            json={
                "name": "B.Tech - Computer Science Engineering",
                "code": "FOENG-D03-P01",
                "department_id": str(department_id),
                "duration_years": 4,
            },
        )
    finally:
        programs_endpoint.db = original_db
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["code"] == "FOENG-D03-P01"
    assert response.json()["total_semesters"] == 8


def test_department_admin_can_create_section() -> None:
    client = TestClient(app)
    original_db = classes_endpoint.db
    classes_endpoint.db = SimpleNamespace(classes=_SimpleCollection())
    app.dependency_overrides[security_core.get_current_user] = _override_user(
        {"_id": str(ObjectId()), "role": "admin", "admin_type": "department_admin", "extended_roles": []}
    )
    try:
        response = client.post(
            "/api/v1/sections/",
            json={"name": "Section A"},
        )
    finally:
        classes_endpoint.db = original_db
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["name"] == "Section A"


def test_department_admin_cannot_create_legacy_course() -> None:
    client = TestClient(app)
    app.dependency_overrides[security_core.get_current_user] = _override_user(
        {"_id": str(ObjectId()), "role": "admin", "admin_type": "department_admin", "extended_roles": []}
    )
    try:
        response = client.post(
            "/api/v1/courses/",
            json={"name": "BCA", "code": "BCA", "description": "Legacy course"},
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 403
    assert response.json()["detail"] == "Missing required permission: courses.manage"
