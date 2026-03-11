from types import SimpleNamespace

from bson import ObjectId
from fastapi.testclient import TestClient

from app.main import app
from app.core import security as security_core
from app.core.permission_registry import ACADEMIC_ROUTE_PERMISSION_MATRIX
from app.api.v1.endpoints import batches as batches_endpoint
from app.api.v1.endpoints import classes as classes_endpoint
from app.api.v1.endpoints import departments as departments_endpoint
from app.api.v1.endpoints import faculties as faculties_endpoint
from app.api.v1.endpoints import programs as programs_endpoint
from app.api.v1.endpoints import semesters as semesters_endpoint


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

    async def insert_many(self, documents):
        inserted_ids = []
        for document in documents:
            inserted_id = ObjectId()
            inserted_ids.append(inserted_id)
            self.items.append({**document, "_id": inserted_id})
        return SimpleNamespace(inserted_ids=inserted_ids)

    def find(self, query, projection=None):
        items = []
        for item in self.items:
            matched = True
            for key, value in query.items():
                if isinstance(value, dict) and "$in" in value:
                    if item.get(key) not in value["$in"]:
                        matched = False
                        break
                else:
                    if item.get(key) != value:
                        matched = False
                        break
            if matched:
                items.append(item)
        return SimpleNamespace(to_list=lambda length=1000: _async_return(items[:length]))

    async def count_documents(self, query):
        rows = await self.find(query).to_list(length=10000)
        return len(rows)

    async def update_many(self, query, update):
        return SimpleNamespace(matched_count=0, modified_count=0)


async def _async_return(value):
    return value


def _override_user(user):
    async def _dependency_override():
        return user

    return _dependency_override


def test_academic_route_permission_matrix_tracks_canonical_write_permissions() -> None:
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/faculties"]["POST"] == "faculties.manage"
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/programs"]["POST"] == "programs.manage"
    assert ACADEMIC_ROUTE_PERMISSION_MATRIX["/sections"]["DELETE"] == "sections.manage"


def test_permission_registry_grants_expected_admin_type_access() -> None:
    department_admin = {"role": "admin", "admin_type": "department_admin", "extended_roles": []}
    academic_admin = {"role": "admin", "admin_type": "academic_admin", "extended_roles": []}
    teacher = {"role": "teacher", "extended_roles": []}

    assert security_core.has_permission(department_admin, "programs.manage") is True
    assert security_core.has_permission(department_admin, "sections.manage") is True
    assert security_core.has_permission(department_admin, "faculties.manage") is False
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
        batches=_SimpleCollection(),
        semesters=_SimpleCollection(),
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
    batch_id = ObjectId()
    semester_id = ObjectId()
    classes_endpoint.db = SimpleNamespace(
        classes=_SimpleCollection(),
        faculties=_SimpleCollection(),
        departments=_SimpleCollection(),
        programs=_SimpleCollection(),
        specializations=_SimpleCollection(),
        batches=_SimpleCollection([{"_id": batch_id, "program_id": None, "specialization_id": None}]),
        semesters=_SimpleCollection([{"_id": semester_id, "batch_id": str(batch_id)}]),
    )
    app.dependency_overrides[security_core.get_current_user] = _override_user(
        {"_id": str(ObjectId()), "role": "admin", "admin_type": "department_admin", "extended_roles": []}
    )
    try:
        response = client.post(
            "/api/v1/sections/",
            json={"name": "Section A", "batch_id": str(batch_id), "semester_id": str(semester_id)},
        )
    finally:
        classes_endpoint.db = original_db
        app.dependency_overrides.clear()

    assert response.status_code == 201
    assert response.json()["name"] == "Section A"


def test_legacy_course_route_is_not_mounted() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/courses/",
        json={"name": "BCA", "code": "BCA", "description": "Legacy course"},
    )
    assert response.status_code == 404


def test_legacy_branch_route_is_not_mounted() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/branches/",
        json={"name": "Computer Science", "code": "CSE", "department_code": "DEP01"},
    )
    assert response.status_code == 404


def test_legacy_class_route_is_not_mounted() -> None:
    client = TestClient(app)
    response = client.post(
        "/api/v1/classes/",
        json={"name": "Section A"},
    )
    assert response.status_code == 404
