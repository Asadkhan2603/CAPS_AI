import asyncio
import re
from types import SimpleNamespace

from bson import ObjectId
import pytest

from app.api.v1.endpoints import batches as batches_endpoint
from app.api.v1.endpoints import classes as classes_endpoint
from app.api.v1.endpoints import programs as programs_endpoint
from app.schemas.batch import BatchCreate
from app.schemas.class_item import ClassCreate
from app.schemas.program import ProgramUpdate
from app.services.academic_batching import build_batch_identity, build_program_batch_prefix
from app.services import governance as governance_service


class _AsyncCursor:
    def __init__(self, items):
        self.items = list(items)
        self._index = 0

    def skip(self, count):
        self.items = self.items[count:]
        return self

    def limit(self, count):
        self.items = self.items[:count]
        return self

    async def to_list(self, length):
        return list(self.items[:length])

    def __aiter__(self):
        self._index = 0
        return self

    async def __anext__(self):
        if self._index >= len(self.items):
            raise StopAsyncIteration
        value = self.items[self._index]
        self._index += 1
        return value


class _InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class _UpdateResult:
    def __init__(self, matched_count=1, modified_count=1):
        self.matched_count = matched_count
        self.modified_count = modified_count


def _matches(document, query):
    for key, expected in query.items():
        actual = document.get(key)
        if isinstance(expected, dict):
            if "$regex" in expected:
                pattern = expected["$regex"]
                flags = re.IGNORECASE if "i" in str(expected.get("$options", "")) else 0
                if re.fullmatch(pattern.strip("^$"), str(actual or ""), flags=flags) is None:
                    return False
            if "$gt" in expected and not (actual is not None and actual > expected["$gt"]):
                return False
            if "$nin" in expected and actual in expected["$nin"]:
                return False
            if "$in" in expected and actual not in expected["$in"]:
                return False
            continue
        if actual != expected:
            return False
    return True


class _MemoryCollection:
    def __init__(self, items=None):
        self.items = list(items or [])

    async def find_one(self, query):
        for item in self.items:
            if _matches(item, query):
                return item
        return None

    def find(self, query, projection=None):
        return _AsyncCursor([item for item in self.items if _matches(item, query)])

    async def insert_one(self, document):
        inserted_id = document.get("_id", ObjectId())
        saved = {**document, "_id": inserted_id}
        self.items.append(saved)
        return _InsertResult(inserted_id)

    async def insert_many(self, documents):
        inserted_ids = []
        for document in documents:
            inserted_id = document.get("_id", ObjectId())
            self.items.append({**document, "_id": inserted_id})
            inserted_ids.append(inserted_id)
        return SimpleNamespace(inserted_ids=inserted_ids)

    async def update_one(self, query, update):
        for item in self.items:
            if not _matches(item, query):
                continue
            for key, value in update.get("$set", {}).items():
                item[key] = value
            for key in update.get("$unset", {}).keys():
                item.pop(key, None)
            return _UpdateResult()
        return _UpdateResult(matched_count=0, modified_count=0)

    async def update_many(self, query, update):
        matched = 0
        for item in self.items:
            if not _matches(item, query):
                continue
            matched += 1
            for key, value in update.get("$set", {}).items():
                item[key] = value
            for key in update.get("$unset", {}).keys():
                item.pop(key, None)
        return _UpdateResult(matched_count=matched, modified_count=matched)


class _SettingsCollection:
    def __init__(self, policy):
        self.policy = policy

    async def find_one(self, query):
        if query.get("key") == "governance_policy":
            return {"key": "governance_policy", "value": self.policy}
        return None


def test_build_program_batch_prefix_uses_course_name_before_specialization() -> None:
    assert build_program_batch_prefix(program_name="B.Sc. (Hons)", program_code="SCI-P01") == "B.Sc."
    assert build_program_batch_prefix(program_name="B.Tech - CSE", program_code="ENG-P01") == "B.Tech"


def test_build_batch_identity_uses_program_display_prefix() -> None:
    name, code = build_batch_identity(program_batch_prefix="B.Sc.", start_year=2022, end_year=2026)

    assert name == "Batch 2022-2026"
    assert code == "B.Sc.-B22-26"


def test_sync_program_semesters_creates_missing_reactivates_inactive_and_archives_extra(monkeypatch) -> None:
    batch_id = ObjectId()
    fake_db = SimpleNamespace(
        batches=_MemoryCollection(
            [
                {
                    "_id": batch_id,
                    "program_id": "program-1",
                    "start_year": 2024,
                    "department_id": "department-1",
                    "university_name": "Medi-Caps University",
                    "university_code": "MEDICAPS",
                }
            ]
        ),
        semesters=_MemoryCollection(
            [
                {"_id": ObjectId(), "batch_id": str(batch_id), "semester_number": 1, "label": "Semester 1", "is_active": True},
                {"_id": ObjectId(), "batch_id": str(batch_id), "semester_number": 2, "label": "Semester 2", "is_active": False},
                {"_id": ObjectId(), "batch_id": str(batch_id), "semester_number": 5, "label": "Semester 5", "is_active": True},
            ]
        ),
    )
    monkeypatch.setattr(programs_endpoint, "db", fake_db)

    asyncio.run(programs_endpoint._sync_program_semesters("program-1", 4))

    by_number = {item["semester_number"]: item for item in fake_db.semesters.items}
    assert sorted(by_number) == [1, 2, 3, 4, 5]
    assert by_number[2]["is_active"] is True
    assert by_number[1]["label"] == "Semester 1 (2024-2025)"
    assert by_number[2]["label"] == "Semester 2 (2024-2025)"
    assert by_number[3]["label"] == "Semester 3 (2025-2026)"
    assert by_number[4]["label"] == "Semester 4 (2025-2026)"
    assert by_number[3]["academic_year_label"] == "2025-2026"
    assert by_number[3]["university_code"] == "MEDICAPS"
    assert by_number[5]["is_active"] is False


def test_update_program_rejects_duration_change_when_students_are_enrolled(monkeypatch) -> None:
    program_id = ObjectId()
    fake_programs = _MemoryCollection(
        [
            {
                "_id": program_id,
                "name": "B.Tech - CSE",
                "code": "FOENG-D03-P01",
                "department_id": "dep-1",
                "duration_years": 4,
                "total_semesters": 8,
                "is_active": True,
            }
        ]
    )
    monkeypatch.setattr(programs_endpoint, "db", SimpleNamespace(programs=fake_programs, departments=_MemoryCollection()))
    monkeypatch.setattr(programs_endpoint, "_program_has_enrolled_semester_students", lambda program_id: asyncio.sleep(0, result=True))

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            programs_endpoint.update_program(
                str(program_id),
                ProgramUpdate(duration_years=5),
                _current_user={"_id": str(ObjectId()), "role": "admin", "admin_type": "academic_admin"},
            )
        )

    error = exc_info.value
    assert getattr(error, "status_code", None) == 409
    assert "already enrolled" in str(getattr(error, "detail", "")).lower()


def test_create_batch_generates_semesters_from_program_duration(monkeypatch) -> None:
    program_id = ObjectId()
    department_id = ObjectId()
    fake_bdb = SimpleNamespace(
        programs=_MemoryCollection(
            [
                {
                    "_id": program_id,
                    "name": "B.Tech - CSE",
                    "code": "FOENG-D03-P01",
                    "department_id": str(department_id),
                    "duration_years": 4,
                    "total_semesters": 8,
                    "is_active": True,
                }
            ]
        ),
        departments=_MemoryCollection(
            [
                {
                    "_id": department_id,
                    "name": "Computer Science",
                    "code": "FOENG-D03",
                    "university_name": "Medi-Caps University",
                    "university_code": "MEDICAPS",
                }
            ]
        ),
        specializations=_MemoryCollection(),
        batches=_MemoryCollection(),
        semesters=_MemoryCollection(),
    )
    monkeypatch.setattr(batches_endpoint, "db", fake_bdb)

    result = asyncio.run(
        batches_endpoint.create_batch(
            BatchCreate(
                program_id=str(program_id),
                specialization_id=None,
                name="2024",
                code="BT-24",
                start_year=2024,
                end_year=None,
            ),
            _current_user={"_id": str(ObjectId()), "role": "admin", "admin_type": "department_admin"},
        )
    )

    assert result.code == "BT-24"
    assert result.start_year == 2024
    assert result.end_year == 2028
    assert result.academic_span_label == "2024-2028"
    assert result.university_code == "MEDICAPS"
    semester_numbers = [item["semester_number"] for item in fake_bdb.semesters.items]
    assert semester_numbers == [1, 2, 3, 4, 5, 6, 7, 8]
    assert all(item["batch_id"] == result.id for item in fake_bdb.semesters.items)
    assert fake_bdb.semesters.items[0]["label"] == "Semester 1 (2024-2025)"
    assert fake_bdb.semesters.items[-1]["label"] == "Semester 8 (2027-2028)"
    assert fake_bdb.semesters.items[0]["academic_year_label"] == "2024-2025"


@pytest.mark.parametrize(
    ("payload", "documents", "expected_detail"),
    [
        (
            {
                "faculty_id": "faculty-1",
                "department_id": "department-1",
                "name": "Section A",
            },
            {
                "faculties": [{"_id": ObjectId("64f100000000000000000001")}],
                "departments": [{"_id": ObjectId("64f100000000000000000011"), "faculty_id": "faculty-2"}],
            },
            "department_id does not belong to provided faculty_id",
        ),
        (
            {
                "department_id": "department-1",
                "program_id": "program-1",
                "name": "Section A",
            },
            {
                "departments": [{"_id": ObjectId("64f100000000000000000021"), "faculty_id": "faculty-1"}],
                "programs": [{"_id": ObjectId("64f100000000000000000031"), "department_id": "department-2"}],
            },
            "program_id does not belong to provided department_id",
        ),
        (
            {
                "program_id": "program-1",
                "specialization_id": "specialization-1",
                "name": "Section A",
            },
            {
                "programs": [{"_id": ObjectId("64f100000000000000000041"), "department_id": "department-1"}],
                "specializations": [{"_id": ObjectId("64f100000000000000000051"), "program_id": "program-2"}],
            },
            "specialization_id does not belong to provided program_id",
        ),
        (
            {
                "batch_id": "batch-1",
                "semester_id": "semester-1",
                "name": "Section A",
            },
            {
                "batches": [{"_id": ObjectId("64f100000000000000000061"), "program_id": "program-1"}],
                "semesters": [{"_id": ObjectId("64f100000000000000000071"), "batch_id": "batch-2"}],
            },
            "semester_id does not belong to provided batch_id",
        ),
    ],
)
def test_create_class_validates_cross_entity_ownership(monkeypatch, payload, documents, expected_detail) -> None:
    fake_db = SimpleNamespace(
        faculties=_MemoryCollection(documents.get("faculties")),
        departments=_MemoryCollection(documents.get("departments")),
        programs=_MemoryCollection(documents.get("programs")),
        specializations=_MemoryCollection(documents.get("specializations")),
        courses=_MemoryCollection(documents.get("courses")),
        years=_MemoryCollection(documents.get("years")),
        batches=_MemoryCollection(documents.get("batches")),
        semesters=_MemoryCollection(documents.get("semesters")),
        classes=_MemoryCollection(),
    )
    monkeypatch.setattr(classes_endpoint, "db", fake_db)

    normalized_payload = {
        "faculty_id": None,
        "department_id": None,
        "program_id": None,
        "specialization_id": None,
        "course_id": None,
        "year_id": None,
        "batch_id": None,
        "semester_id": None,
        "name": "Section A",
        "faculty_name": None,
        "class_coordinator_user_id": None,
    }
    normalized_payload.update(payload)

    if normalized_payload["faculty_id"] == "faculty-1":
        normalized_payload["faculty_id"] = str(documents["faculties"][0]["_id"])
    if normalized_payload["department_id"] == "department-1":
        normalized_payload["department_id"] = str(documents["departments"][0]["_id"])
    if normalized_payload["program_id"] == "program-1":
        normalized_payload["program_id"] = str(documents["programs"][0]["_id"])
    if normalized_payload["specialization_id"] == "specialization-1":
        normalized_payload["specialization_id"] = str(documents["specializations"][0]["_id"])
    if normalized_payload["batch_id"] == "batch-1":
        normalized_payload["batch_id"] = str(documents["batches"][0]["_id"])
    if normalized_payload["semester_id"] == "semester-1":
        normalized_payload["semester_id"] = str(documents["semesters"][0]["_id"])

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            classes_endpoint.create_class(
                ClassCreate(**normalized_payload),
                _current_user={"_id": str(ObjectId()), "role": "admin", "admin_type": "department_admin"},
            )
        )

    error = exc_info.value
    assert getattr(error, "status_code", None) == 400
    assert getattr(error, "detail", None) == expected_detail


def test_delete_class_requires_review_id_when_two_person_rule_enabled(monkeypatch) -> None:
    class_id = ObjectId()
    fake_classes = _MemoryCollection([{"_id": class_id, "name": "Section A", "is_active": True}])
    monkeypatch.setattr(classes_endpoint, "db", SimpleNamespace(classes=fake_classes))
    monkeypatch.setattr(
        governance_service,
        "db",
        SimpleNamespace(settings=_SettingsCollection({"two_person_rule_enabled": True})),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            classes_endpoint.delete_class(
                str(class_id),
                review_id=None,
                current_user={"_id": ObjectId(), "role": "admin", "admin_type": "super_admin"},
            )
        )

    error = exc_info.value
    assert getattr(error, "status_code", None) == 403
    assert "review_id" in str(getattr(error, "detail", "")).lower()
    assert fake_classes.items[0]["is_active"] is True
