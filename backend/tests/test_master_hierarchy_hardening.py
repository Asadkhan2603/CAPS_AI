import asyncio
from types import SimpleNamespace

from bson import ObjectId
import pytest

from app.api.v1.endpoints import departments as departments_endpoint
from app.api.v1.endpoints import faculties as faculties_endpoint
from app.api.v1.endpoints import programs as programs_endpoint
from app.api.v1.endpoints import specializations as specializations_endpoint
from app.api.v1.endpoints import universities as universities_endpoint
from app.schemas.department import DepartmentCreate
from app.schemas.faculty import FacultyUpdate
from app.schemas.program import ProgramUpdate


class _CountCollection:
    def __init__(self, *, count: int = 0, item: dict | None = None) -> None:
        self.count = count
        self.item = item
        self.updated_query = None
        self.updated_payload = None

    async def count_documents(self, query):
        return self.count

    async def find_one(self, query):
        if self.item is None:
            return None
        if query.get("_id") == self.item.get("_id"):
            return self.item
        if query.get("faculty_id") == self.item.get("faculty_id"):
            return self.item
        if query.get("university_id") == self.item.get("university_id"):
            return self.item
        return None

    async def update_one(self, query, update):
        self.updated_query = query
        self.updated_payload = update
        return SimpleNamespace(matched_count=1)


def test_delete_university_is_blocked_when_faculties_exist(monkeypatch) -> None:
    university_id = ObjectId()
    monkeypatch.setattr(
        universities_endpoint,
        "db",
        SimpleNamespace(
            universities=_CountCollection(item={"_id": university_id, "university_id": "UM"}),
            faculties=_CountCollection(count=2),
        ),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(universities_endpoint.delete_university(str(university_id), _current_user={"role": "admin"}))

    assert getattr(exc_info.value, "status_code", None) == 409
    assert "faculties" in str(getattr(exc_info.value, "detail", "")).lower()


def test_update_faculty_blocks_university_move_when_departments_exist(monkeypatch) -> None:
    faculty_id = ObjectId()
    current_university_id = ObjectId()
    next_university_id = ObjectId()
    monkeypatch.setattr(
        faculties_endpoint,
        "db",
        SimpleNamespace(
            faculties=_CountCollection(
                item={
                    "_id": faculty_id,
                    "faculty_id": "FAC-ENG",
                    "faculty_code": "ENG",
                    "faculty_name": "Faculty of Engineering",
                    "university_id": str(current_university_id),
                }
            ),
            universities=_CountCollection(item={"_id": next_university_id, "university_id": "UM", "university_name": "UM University"}),
            departments=_CountCollection(count=1),
            users=_CountCollection(count=0),
            classes=_CountCollection(count=0),
        ),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            faculties_endpoint.update_faculty(
                str(faculty_id),
                FacultyUpdate(university_id=str(next_university_id)),
                _current_user={"role": "admin"},
            )
        )

    assert getattr(exc_info.value, "status_code", None) == 409
    assert "move to another university" in str(getattr(exc_info.value, "detail", "")).lower()


def test_create_department_requires_existing_faculty(monkeypatch) -> None:
    monkeypatch.setattr(
        departments_endpoint,
        "db",
        SimpleNamespace(
            faculties=_CountCollection(item=None),
            departments=_CountCollection(),
        ),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            departments_endpoint.create_department(
                DepartmentCreate(department_name="Department of AI", department_code="AI"),
                _current_user={"role": "admin"},
            )
        )

    assert getattr(exc_info.value, "status_code", None) == 400
    assert "existing faculty" in str(getattr(exc_info.value, "detail", "")).lower()


def test_update_program_rejects_manual_lineage_override(monkeypatch) -> None:
    program_id = ObjectId()
    monkeypatch.setattr(
        programs_endpoint,
        "db",
        SimpleNamespace(
            programs=_CountCollection(
                item={
                    "_id": program_id,
                    "program_id": "PRG-ENG-CSE-BTECH-CSE",
                    "program_code": "BTECH-CSE",
                    "program_name": "B.Tech CSE",
                    "department_id": str(ObjectId()),
                    "duration_years": 4,
                    "total_semesters": 8,
                }
            )
        ),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            programs_endpoint.update_program(
                str(program_id),
                ProgramUpdate(department_name="Manual Override"),
                _current_user={"role": "admin"},
            )
        )

    assert getattr(exc_info.value, "status_code", None) == 400
    assert "derived from the selected department" in str(getattr(exc_info.value, "detail", "")).lower()


def test_delete_program_is_blocked_when_batches_exist(monkeypatch) -> None:
    program_id = ObjectId()
    monkeypatch.setattr(
        programs_endpoint,
        "db",
        SimpleNamespace(
            specializations=_CountCollection(count=0),
            batches=_CountCollection(count=3),
            semesters=_CountCollection(count=0),
            classes=_CountCollection(count=0),
            users=_CountCollection(count=0),
            programs=_CountCollection(item={"_id": program_id}),
        ),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(programs_endpoint.delete_program(str(program_id), current_user={"_id": ObjectId(), "admin_type": "super_admin"}))

    assert getattr(exc_info.value, "status_code", None) == 409
    assert "batches" in str(getattr(exc_info.value, "detail", "")).lower()


def test_delete_specialization_is_blocked_when_descendants_exist(monkeypatch) -> None:
    specialization_id = ObjectId()
    monkeypatch.setattr(
        specializations_endpoint,
        "db",
        SimpleNamespace(
            batches=_CountCollection(count=1),
            semesters=_CountCollection(count=0),
            classes=_CountCollection(count=0),
            users=_CountCollection(count=0),
            specializations=_CountCollection(item={"_id": specialization_id}),
        ),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            specializations_endpoint.delete_specialization(
                str(specialization_id),
                current_user={"_id": ObjectId(), "admin_type": "super_admin"},
            )
        )

    assert getattr(exc_info.value, "status_code", None) == 409
    assert "batches" in str(getattr(exc_info.value, "detail", "")).lower()
