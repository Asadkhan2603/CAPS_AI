import asyncio
import csv
import json
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from io import StringIO
from types import SimpleNamespace
from typing import Any, Dict, List

from bson import ObjectId
from fastapi.testclient import TestClient
from pymongo.errors import DuplicateKeyError
import pyotp

from app.main import app
from app.api.v1.endpoints import ai as ai_endpoint
from app.api.v1.endpoints import assignments as assignments_endpoint
from app.api.v1.endpoints import analytics as analytics_endpoint
from app.api.v1.endpoints import admin_system as admin_system_endpoint
from app.api.v1.endpoints import admin_analytics as admin_analytics_endpoint
from app.api.v1.endpoints import admin_communication as admin_communication_endpoint
from app.api.v1.endpoints import audit_logs as audit_logs_endpoint
from app.api.v1.endpoints import club_events as club_events_endpoint
from app.api.v1.endpoints import clubs as clubs_endpoint
from app.api.v1.endpoints import departments as departments_endpoint
from app.api.v1.endpoints import enrollments as enrollments_endpoint
from app.api.v1.endpoints import event_registrations as event_registrations_endpoint
from app.api.v1.endpoints import exams as exams_endpoint
from app.api.v1.endpoints import faculties as faculties_endpoint
from app.api.v1.endpoints import groups as groups_endpoint
from app.api.v1.endpoints import auth as auth_endpoint
from app.api.v1.endpoints import branding as branding_endpoint
from app.api.v1.endpoints import class_slots as class_slots_endpoint
from app.api.v1.endpoints import classes as classes_endpoint
from app.api.v1.endpoints import course_offerings as course_offerings_endpoint
from app.api.v1.endpoints import evaluations as evaluations_endpoint
from app.api.v1.endpoints import evaluations_results as evaluations_results_endpoint
from app.api.v1.endpoints import notices as notices_endpoint
from app.api.v1.endpoints import notifications as notifications_endpoint
from app.api.v1.endpoints import programs as programs_endpoint
from app.api.v1.endpoints import review_tickets as review_tickets_endpoint
from app.api.v1.endpoints import batches as batches_endpoint
from app.api.v1.endpoints import semesters as semesters_endpoint
from app.api.v1.endpoints import similarity as similarity_endpoint
from app.api.v1.endpoints import students as students_endpoint
from app.api.v1.endpoints import submissions as submissions_endpoint
from app.api.v1.endpoints import timetables as timetables_endpoint
from app.api.v1.endpoints import subjects as subjects_endpoint
from app.api.v1.endpoints import users as users_endpoint
from app.core.config import settings
from app.core import security as security_core
from app.domains.auth.repository import AuthRepository
from app.domains.auth import service as auth_service_module
from app.services import ai_runtime as ai_runtime_service
from app.services import analytics_snapshot as analytics_snapshot_service
from app.services import audit as audit_service
from app.services import club_governance as club_governance_service
from app.services import club_permissions as club_permissions_service
from app.services import club_queue_insights as club_queue_insights_service
from app.services import communication_deliveries as communication_deliveries_service
from app.services import communication_digests as communication_digests_service
from app.services import communication_preferences as communication_preferences_service
from app.services import notifications as notifications_service
from app.services import operational_alert_routing as operational_alert_routing_service
from app.services import similarity_pipeline as similarity_pipeline_service
from app.services import student_profiles as student_profiles_service
from app.services import submission_ai as submission_ai_service
from app.services import background_jobs as background_jobs_service


@dataclass
class InsertOneResult:
    inserted_id: ObjectId


@dataclass
class InsertManyResult:
    inserted_ids: List[ObjectId]


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

    def sort(self, key_or_list, direction=None) -> "FakeCursor":
        if isinstance(key_or_list, list):
            # Apply stable multi-key sort from last to first.
            for key, dir_value in reversed(key_or_list):
                reverse = dir_value == -1
                self.items.sort(key=lambda item: item.get(key), reverse=reverse)
            return self
        if isinstance(key_or_list, str):
            reverse = direction == -1
            self.items.sort(key=lambda item: item.get(key_or_list), reverse=reverse)
            return self
        return self

    def batch_size(self, amount: int) -> "FakeCursor":
        _ = amount
        return self

    def __aiter__(self):
        self._iter_index = 0
        return self

    async def __anext__(self):
        if self._iter_index >= len(self.items):
            raise StopAsyncIteration
        value = self.items[self._iter_index]
        self._iter_index += 1
        return value


class FakeUsersCollection:
    def __init__(self, *, enforce_email_unique: bool = False) -> None:
        self.items: List[Dict[str, Any]] = []
        self.enforce_email_unique = enforce_email_unique

    async def find_one(self, query: Dict[str, Any], projection: Dict[str, Any] | None = None, sort=None) -> Dict[str, Any] | None:
        items = [item for item in self.items if _matches_query(item, query)]
        if sort:
            if isinstance(sort, list):
                for key, dir_value in reversed(sort):
                    reverse = dir_value == -1
                    items.sort(key=lambda row: row.get(key), reverse=reverse)
            elif isinstance(sort, tuple):
                key, dir_value = sort
                items.sort(key=lambda row: row.get(key), reverse=(dir_value == -1))
        for item in items:
            if _matches_query(item, query):
                return item
        return None

    async def create_index(self, key, unique: bool = False, **kwargs) -> None:
        _ = (key, unique, kwargs)

    async def insert_one(self, document: Dict[str, Any]) -> InsertOneResult:
        if self.enforce_email_unique and "email" in document and document["email"] is not None:
            for item in self.items:
                if item.get("email") == document["email"]:
                    raise Exception("duplicate key")
        inserted_id = ObjectId()
        saved = {**document, "_id": inserted_id}
        self.items.append(saved)
        return InsertOneResult(inserted_id=inserted_id)

    async def insert_many(self, documents: List[Dict[str, Any]], ordered: bool = True) -> InsertManyResult:
        _ = ordered
        inserted_ids: List[ObjectId] = []
        for document in documents:
            inserted_id = ObjectId()
            inserted_ids.append(inserted_id)
            self.items.append({**document, "_id": inserted_id})
        return InsertManyResult(inserted_ids=inserted_ids)

    def find(self, query: Dict[str, Any], projection: Dict[str, Any] | None = None) -> FakeCursor:
        return FakeCursor([item for item in self.items if _matches_query(item, query)])

    async def count_documents(self, query: Dict[str, Any]) -> int:
        return len([item for item in self.items if _matches_query(item, query)])

    async def distinct(self, key: str, query: Dict[str, Any] | None = None) -> List[Any]:
        values: List[Any] = []
        for item in self.items:
            if not _matches_query(item, query or {}):
                continue
            value = item.get(key)
            if value not in values:
                values.append(value)
        return values

    async def update_one(self, query: Dict[str, Any], update: Dict[str, Any], upsert: bool = False):
        matched = 0
        for item in self.items:
            if _matches_query(item, query):
                matched += 1
                item.update(update.get("$set", {}))
                break
        if matched == 0 and upsert:
            document = dict(update.get("$set", {}))
            for key, value in query.items():
                if isinstance(value, dict):
                    continue
                document.setdefault(key, value)
            document.setdefault("_id", ObjectId())
            self.items.append(document)
            return type("UpdateResult", (), {"matched_count": 0, "upserted_id": document["_id"]})()
        return type("UpdateResult", (), {"matched_count": matched, "upserted_id": None})()

    async def find_one_and_update(
        self,
        query: Dict[str, Any],
        update: Dict[str, Any],
        sort=None,
        return_document=None,
    ) -> Dict[str, Any] | None:
        _ = return_document
        items = [item for item in self.items if _matches_query(item, query)]
        if sort:
            if isinstance(sort, list):
                for key, dir_value in reversed(sort):
                    reverse = dir_value == -1
                    items.sort(key=lambda row: row.get(key), reverse=reverse)
            elif isinstance(sort, tuple):
                key, dir_value = sort
                items.sort(key=lambda row: row.get(key), reverse=(dir_value == -1))
        if not items:
            return None
        target = items[0]
        target.update(update.get("$set", {}))
        return target

    async def update_many(self, query: Dict[str, Any], update: Dict[str, Any]):
        matched = 0
        for item in self.items:
            if _matches_query(item, query):
                matched += 1
                item.update(update.get("$set", {}))
        return type("UpdateManyResult", (), {"matched_count": matched, "modified_count": matched})()

    async def delete_one(self, query: Dict[str, Any]):
        deleted = 0
        for index, item in enumerate(self.items):
            if _matches_query(item, query):
                self.items.pop(index)
                deleted = 1
                break
        return type("DeleteResult", (), {"deleted_count": deleted})()

    async def delete_many(self, query: Dict[str, Any]):
        original_count = len(self.items)
        self.items = [item for item in self.items if not _matches_query(item, query)]
        deleted = original_count - len(self.items)
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
        if isinstance(value, dict) and "$ne" in value:
            if item.get(key) == value["$ne"]:
                return False
            continue
        if isinstance(value, dict) and "$exists" in value:
            exists_expected = bool(value["$exists"])
            has_key = key in item
            if has_key != exists_expected:
                return False
            continue
        if isinstance(value, dict) and "$lte" in value:
            if item.get(key) is None or item.get(key) > value["$lte"]:
                return False
            continue
        if isinstance(value, dict) and "$lt" in value:
            if item.get(key) is None or item.get(key) >= value["$lt"]:
                return False
            continue
        if isinstance(value, dict) and "$gte" in value:
            if item.get(key) is None or item.get(key) < value["$gte"]:
                return False
            continue
        if item.get(key) != value:
            return False
    return True


class FakeDB:
    def __init__(self) -> None:
        self.users = FakeUsersCollection(enforce_email_unique=True)
        self.user_sessions = FakeUsersCollection()
        self.token_blacklist = FakeUsersCollection()
        self.faculties = FakeUsersCollection()
        self.departments = FakeUsersCollection()
        self.programs = FakeUsersCollection()
        self.specializations = FakeUsersCollection()
        self.batches = FakeUsersCollection()
        self.batch_read_models = FakeUsersCollection()
        self.semesters = FakeUsersCollection()
        self.semester_read_models = FakeUsersCollection()
        self.courses = FakeUsersCollection()
        self.years = FakeUsersCollection()
        self.classes = FakeUsersCollection()
        self.section_read_models = FakeUsersCollection()
        self.groups = FakeUsersCollection()
        self.students = FakeUsersCollection()
        self.subjects = FakeUsersCollection()
        self.course_offerings = FakeUsersCollection()
        self.course_offering_read_models = FakeUsersCollection()
        self.class_slots = FakeUsersCollection()
        self.class_slot_read_models = FakeUsersCollection()
        self.attendance_records = FakeUsersCollection()
        self.assignments = FakeUsersCollection()
        self.submissions = FakeUsersCollection()
        self.ai_evaluation_chats = FakeUsersCollection()
        self.ai_evaluation_runs = FakeUsersCollection()
        self.ai_jobs = FakeUsersCollection()
        self.ai_similarity_views = FakeUsersCollection()
        self.evaluations = FakeUsersCollection()
        self.semester_results = FakeUsersCollection()
        self.exams = FakeUsersCollection()
        self.grievances = FakeUsersCollection()
        self.student_interventions = FakeUsersCollection()
        self.similarity_logs = FakeUsersCollection()
        self.notifications = FakeUsersCollection()
        self.communication_deliveries = FakeUsersCollection()
        self.communication_digests = FakeUsersCollection()
        self.notices = FakeUsersCollection()
        self.clubs = FakeUsersCollection()
        self.club_members = FakeUsersCollection()
        self.club_applications = FakeUsersCollection()
        self.club_events = FakeUsersCollection()
        self.event_registrations = FakeUsersCollection()
        self.club_queue_views = FakeUsersCollection()
        self.club_queue_snapshots = FakeUsersCollection()
        self.audit_logs = FakeUsersCollection()
        self.enrollments = FakeUsersCollection()
        self.review_tickets = FakeUsersCollection()
        self.timetables = FakeUsersCollection()
        self.timetable_subject_teacher_maps = FakeUsersCollection()
        self.settings = FakeUsersCollection()
        self.internship_sessions = FakeUsersCollection()
        self.scheduler_locks = FakeUsersCollection()
        self.system_health_snapshots = FakeUsersCollection()
        self.analytics_snapshots = FakeUsersCollection()
        self.operational_alert_routes = FakeUsersCollection()

    async def command(self, name: str) -> dict[str, Any]:
        if name != "ping":
            raise ValueError(f"Unsupported command: {name}")
        return {"ok": 1}

    def __getitem__(self, name: str) -> FakeUsersCollection:
        return getattr(self, name)


def _setup_fake_db() -> FakeDB:
    fake_db = FakeDB()
    auth_endpoint.db = fake_db
    users_endpoint.db = fake_db
    faculties_endpoint.db = fake_db
    departments_endpoint.db = fake_db
    programs_endpoint.db = fake_db
    batches_endpoint.db = fake_db
    semesters_endpoint.db = fake_db
    classes_endpoint.db = fake_db
    course_offerings_endpoint.db = fake_db
    class_slots_endpoint.db = fake_db
    groups_endpoint.db = fake_db
    students_endpoint.db = fake_db
    subjects_endpoint.db = fake_db
    assignments_endpoint.db = fake_db
    submissions_endpoint.db = fake_db
    ai_endpoint.db = fake_db
    evaluations_endpoint.db = fake_db
    evaluations_results_endpoint.db = fake_db
    similarity_endpoint.db = fake_db
    analytics_endpoint.db = fake_db
    admin_system_endpoint.db = fake_db
    admin_analytics_endpoint.db = fake_db
    admin_communication_endpoint.db = fake_db
    branding_endpoint.db = fake_db
    notifications_endpoint.db = fake_db
    notices_endpoint.db = fake_db
    clubs_endpoint.db = fake_db
    club_events_endpoint.db = fake_db
    event_registrations_endpoint.db = fake_db
    exams_endpoint.db = fake_db
    club_governance_service.db = fake_db
    club_permissions_service.db = fake_db
    club_queue_insights_service.db = fake_db
    review_tickets_endpoint.db = fake_db
    audit_logs_endpoint.db = fake_db
    enrollments_endpoint.db = fake_db
    timetables_endpoint.db = fake_db
    notifications_service.db = fake_db
    communication_deliveries_service.db = fake_db
    communication_digests_service.db = fake_db
    communication_preferences_service.db = fake_db
    background_jobs_service.db = fake_db
    operational_alert_routing_service.db = fake_db
    audit_service.db = fake_db
    ai_runtime_service.db = fake_db
    analytics_snapshot_service.db = fake_db
    similarity_pipeline_service.db = fake_db
    student_profiles_service.db = fake_db
    submission_ai_service.db = fake_db
    security_core.db = fake_db
    return fake_db


def _register_and_login(
    client: TestClient,
    *,
    full_name: str,
    email: str,
    role: str,
    password: str = "password123",
    extended_roles: list[str] | None = None,
):
    payload: dict[str, Any] = {
        "full_name": full_name,
        "email": email,
        "password": password,
        "role": role,
    }
    if extended_roles:
        payload["extended_roles"] = extended_roles

    register = client.post("/api/v1/auth/register", json=payload)
    assert register.status_code == 201, register.text
    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    return register.json(), {"Authorization": f"Bearer {login.json()['access_token']}"}


def _login_with_headers(
    client: TestClient,
    *,
    email: str,
    password: str = "password123",
    fingerprint: str,
    user_agent: str = "pytest-browser",
    forwarded_for: str = "127.0.0.1",
) -> tuple[dict[str, Any], dict[str, str]]:
    headers = {
        "X-Device-Fingerprint": fingerprint,
        "User-Agent": user_agent,
        "X-Forwarded-For": forwarded_for,
    }
    response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers=headers,
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    headers["Authorization"] = f"Bearer {payload['access_token']}"
    return payload, headers


def _build_webauthn_client_data(origin: str) -> str:
    return auth_service_module.AuthService._b64url_encode(
        json.dumps({"type": "webauthn.get", "challenge": "test-challenge", "origin": origin}).encode("utf-8")
    )


def _install_webauthn_test_mocks(
    monkeypatch,
    *,
    registration_challenge: str = "registration-challenge",
    authentication_challenge: str = "authentication-challenge",
    authentication_sign_count: int = 1,
) -> None:
    monkeypatch.setattr(auth_service_module, "WEBAUTHN_AVAILABLE", True)
    monkeypatch.setattr(
        auth_service_module,
        "generate_registration_options",
        lambda **kwargs: SimpleNamespace(challenge=registration_challenge),
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "generate_authentication_options",
        lambda **kwargs: SimpleNamespace(challenge=authentication_challenge),
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "options_to_json",
        lambda options: json.dumps({"challenge": options.challenge}),
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "verify_registration_response",
        lambda **kwargs: SimpleNamespace(
            credential_id=b"credential-1",
            credential_public_key=b"public-key-1",
            sign_count=0,
            credential_device_type="single_device",
            credential_backed_up=False,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "verify_authentication_response",
        lambda **kwargs: SimpleNamespace(
            new_sign_count=authentication_sign_count,
            credential_device_type="single_device",
            credential_backed_up=False,
        ),
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "base64url_to_bytes",
        lambda value: value.encode("utf-8") if isinstance(value, str) else value,
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "PublicKeyCredentialDescriptor",
        lambda **kwargs: kwargs,
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "AuthenticatorSelectionCriteria",
        lambda **kwargs: kwargs,
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "AuthenticatorAttachment",
        SimpleNamespace(PLATFORM="platform", CROSS_PLATFORM="cross-platform"),
        raising=False,
    )
    monkeypatch.setattr(
        auth_service_module,
        "UserVerificationRequirement",
        SimpleNamespace(PREFERRED="preferred"),
        raising=False,
    )


def _seed_canonical_structure(
    fake_db: FakeDB,
    *,
    suffix: str,
    duration_years: int = 4,
    start_year: int = 2024,
    semester_number: int = 1,
) -> dict[str, str | int]:
    faculty_id = ObjectId()
    department_id = ObjectId()
    program_id = ObjectId()
    batch_id = ObjectId()
    semester_id = ObjectId()
    end_year = start_year + duration_years

    fake_db.faculties.items.append(
        {
            "_id": faculty_id,
            "name": f"Faculty {suffix}",
            "code": f"FAC{suffix}",
            "is_active": True,
        }
    )
    fake_db.departments.items.append(
        {
            "_id": department_id,
            "name": f"Department {suffix}",
            "code": f"DEP{suffix}",
            "faculty_id": str(faculty_id),
            "is_active": True,
        }
    )
    fake_db.programs.items.append(
        {
            "_id": program_id,
            "name": f"Program {suffix}",
            "code": f"PROG{suffix}",
            "department_id": str(department_id),
            "duration_years": duration_years,
            "total_semesters": duration_years * 2,
            "is_active": True,
        }
    )
    fake_db.batches.items.append(
        {
            "_id": batch_id,
            "faculty_id": str(faculty_id),
            "department_id": str(department_id),
            "program_id": str(program_id),
            "specialization_id": None,
            "name": f"Batch {start_year}-{end_year}",
            "code": f"PROG{suffix}-B{str(start_year)[-2:]}-{str(end_year)[-2:]}",
            "start_year": start_year,
            "end_year": end_year,
            "academic_span_label": f"{start_year}-{end_year}",
            "is_active": True,
        }
    )
    fake_db.semesters.items.append(
        {
            "_id": semester_id,
            "batch_id": str(batch_id),
            "faculty_id": str(faculty_id),
            "department_id": str(department_id),
            "program_id": str(program_id),
            "specialization_id": None,
            "semester_number": semester_number,
            "label": f"Semester {semester_number}",
            "is_active": True,
        }
    )

    return {
        "faculty_id": str(faculty_id),
        "department_id": str(department_id),
        "program_id": str(program_id),
        "batch_id": str(batch_id),
        "semester_id": str(semester_id),
        "start_year": start_year,
        "end_year": end_year,
    }


def _create_section_payload(
    structure: dict[str, str | int],
    *,
    name: str,
    class_coordinator_user_id: str | None = None,
    **overrides,
) -> dict[str, str]:
    payload = {
        "faculty_id": str(structure["faculty_id"]),
        "department_id": str(structure["department_id"]),
        "program_id": str(structure["program_id"]),
        "batch_id": str(structure["batch_id"]),
        "semester_id": str(structure["semester_id"]),
        "name": name,
    }
    if class_coordinator_user_id:
        payload["class_coordinator_user_id"] = class_coordinator_user_id
    payload.update({key: value for key, value in overrides.items() if value is not None})
    return payload


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


def test_login_without_mfa_returns_full_tokens() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "No MFA User",
            "email": "nomfa@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "nomfa@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    body = login.json()
    assert body["access_token"]
    assert body["mfa_required"] is False
    assert body["pending_mfa_token"] is None
    assert body["mfa_methods"] == []


def test_totp_mfa_login_requires_pending_token_and_verifies() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "TOTP MFA User",
            "email": "totp_mfa@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "totp_mfa@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    auth_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    enable_totp = client.post("/api/v1/auth/mfa/totp/enable", headers=auth_headers)
    assert enable_totp.status_code == 200
    secret = enable_totp.json()["secret"]
    confirm_code = pyotp.TOTP(secret).now()

    confirm_totp = client.post(
        "/api/v1/auth/mfa/totp/confirm",
        json={"otp_code": confirm_code},
        headers=auth_headers,
    )
    assert confirm_totp.status_code == 200

    mfa_login = client.post(
        "/api/v1/auth/login",
        json={"email": "totp_mfa@example.com", "password": "password123"},
    )
    assert mfa_login.status_code == 200
    mfa_login_body = mfa_login.json()
    assert mfa_login_body["mfa_required"] is True
    assert mfa_login_body["pending_mfa_token"]
    assert "totp" in mfa_login_body["mfa_methods"]

    verify = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "pending_mfa_token": mfa_login_body["pending_mfa_token"],
            "mfa_method": "totp",
            "mfa_code": pyotp.TOTP(secret).now(),
        },
    )
    assert verify.status_code == 200
    verify_body = verify.json()
    assert verify_body["access_token"]
    assert verify_body["mfa_required"] is False


def test_backup_code_can_complete_mfa_only_once() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Backup MFA User",
            "email": "backup_mfa@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "backup_mfa@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    auth_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    enable_totp = client.post("/api/v1/auth/mfa/totp/enable", headers=auth_headers)
    assert enable_totp.status_code == 200
    enable_payload = enable_totp.json()
    backup_code = enable_payload["backup_codes"][0]
    secret = enable_payload["secret"]

    confirm_totp = client.post(
        "/api/v1/auth/mfa/totp/confirm",
        json={"otp_code": pyotp.TOTP(secret).now()},
        headers=auth_headers,
    )
    assert confirm_totp.status_code == 200

    first_login = client.post(
        "/api/v1/auth/login",
        json={"email": "backup_mfa@example.com", "password": "password123"},
    )
    assert first_login.status_code == 200
    first_pending = first_login.json()["pending_mfa_token"]
    assert first_pending

    first_verify = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "pending_mfa_token": first_pending,
            "mfa_method": "backup",
            "mfa_code": backup_code,
        },
    )
    assert first_verify.status_code == 200

    second_login = client.post(
        "/api/v1/auth/login",
        json={"email": "backup_mfa@example.com", "password": "password123"},
    )
    assert second_login.status_code == 200
    second_pending = second_login.json()["pending_mfa_token"]
    assert second_pending

    second_verify = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "pending_mfa_token": second_pending,
            "mfa_method": "backup",
            "mfa_code": backup_code,
        },
    )
    assert second_verify.status_code == 401


def test_sms_mfa_enrollment_and_pending_login_verification() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "SMS MFA User",
            "email": "sms_mfa@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "sms_mfa@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    auth_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    send_enroll = client.post(
        "/api/v1/auth/mfa/sms/enroll/send",
        json={"phone_number": "+15551234567"},
        headers=auth_headers,
    )
    assert send_enroll.status_code == 200
    send_enroll_payload = send_enroll.json()
    assert send_enroll_payload.get("otp_dev")

    verify_enroll = client.post(
        "/api/v1/auth/mfa/sms/enroll/verify",
        json={"otp_code": send_enroll_payload["otp_dev"]},
        headers=auth_headers,
    )
    assert verify_enroll.status_code == 200

    mfa_login = client.post(
        "/api/v1/auth/login",
        json={"email": "sms_mfa@example.com", "password": "password123"},
    )
    assert mfa_login.status_code == 200
    mfa_login_payload = mfa_login.json()
    assert mfa_login_payload["mfa_required"] is True
    assert mfa_login_payload["mfa_primary_method"] == "sms"
    assert "sms" in mfa_login_payload["mfa_methods"]

    challenge = mfa_login_payload.get("mfa_challenge") or {}
    assert challenge.get("challenge_sent") is True
    assert challenge.get("otp_dev")

    verify_login = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "pending_mfa_token": mfa_login_payload["pending_mfa_token"],
            "mfa_method": "sms",
            "mfa_code": challenge["otp_dev"],
        },
    )
    assert verify_login.status_code == 200
    assert verify_login.json()["access_token"]


def test_login_includes_webauthn_method_when_enabled() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "WebAuthn MFA User",
            "email": "webauthn_mfa@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert register.status_code == 201

    created_user = fake_db.users.items[0]
    created_user["mfa_webauthn_enabled"] = True
    created_user["mfa_webauthn_credentials"] = [
        {
            "credential_id": "credential-1",
            "public_key": "public-key-1",
            "sign_count": 0,
            "label": "Security Key",
            "transports": ["usb"],
        }
    ]
    created_user["mfa_primary_method"] = "webauthn"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "webauthn_mfa@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    payload = login.json()
    assert payload["mfa_required"] is True
    assert payload["mfa_primary_method"] == "webauthn"
    assert "webauthn" in payload["mfa_methods"]


def test_security_settings_me_returns_expected_mfa_contract() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Security Settings User",
            "email": "security_settings@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "security_settings@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    security_settings = client.get(
        "/api/v1/auth/security-settings/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert security_settings.status_code == 200
    payload = security_settings.json()
    assert "mfa_enabled" in payload
    assert "mfa_methods" in payload
    assert "primary_method" in payload
    assert "method_status" in payload
    assert "webauthn_credentials" in payload
    assert "recovery_codes_remaining" in payload


def test_security_settings_me_uses_unknown_password_strength_without_metadata() -> None:
    _setup_fake_db()
    client = TestClient(app)

    _register_and_login(
        client,
        full_name="Security Strength User",
        email="security_strength@example.com",
        role="teacher",
    )
    _, auth_headers = _login_with_headers(
        client,
        email="security_strength@example.com",
        fingerprint="security-strength-device",
    )

    security_settings = client.get(
        "/api/v1/auth/security-settings/me",
        headers=auth_headers,
    )
    assert security_settings.status_code == 200
    assert security_settings.json()["password_strength"] == "unknown"


def test_account_activity_marks_current_session_from_request_fingerprint() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Activity User",
            "email": "activity_user@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )

    _login_with_headers(
        client,
        email="activity_user@example.com",
        fingerprint="activity-other-device",
        user_agent="pytest-browser-other",
        forwarded_for="10.0.0.7",
    )
    _, current_headers = _login_with_headers(
        client,
        email="activity_user@example.com",
        fingerprint="activity-current-device",
        user_agent="pytest-browser-current",
        forwarded_for="10.0.0.8",
    )

    assert len(fake_db.user_sessions.items) == 2

    activity = client.get("/api/v1/auth/account-activity/me", headers=current_headers)
    assert activity.status_code == 200
    payload = activity.json()
    assert payload["total_sessions"] == 2
    assert any(session["is_current"] is True for session in payload["active_sessions"])
    assert all(session["session_id"] for session in payload["active_sessions"])


def test_canonical_session_termination_revokes_target_session_and_blacklists_refresh_jti() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Session Owner",
            "email": "session_owner@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )

    _login_with_headers(
        client,
        email="session_owner@example.com",
        fingerprint="owner-other-device",
        user_agent="pytest-browser-other",
        forwarded_for="10.0.0.7",
    )
    _, current_headers = _login_with_headers(
        client,
        email="session_owner@example.com",
        fingerprint="owner-current-device",
        user_agent="pytest-browser-current",
        forwarded_for="10.0.0.8",
    )

    target_session = next(
        session
        for session in fake_db.user_sessions.items
        if session.get("fingerprint") != fake_db.user_sessions.items[-1].get("fingerprint")
    )
    response = client.post(
        f"/api/v1/auth/sessions/{target_session['_id']}/terminate",
        headers=current_headers,
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["session_id"] == str(target_session["_id"])
    assert target_session["revoked_at"] is not None
    assert any(item["jti"] == target_session["refresh_jti"] for item in fake_db.token_blacklist.items)


def test_logout_session_compatibility_route_uses_same_termination_logic() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Compatibility User",
            "email": "compatibility_user@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )

    _login_with_headers(
        client,
        email="compatibility_user@example.com",
        fingerprint="compat-other-device",
        user_agent="pytest-browser-other",
        forwarded_for="10.0.1.7",
    )
    _, current_headers = _login_with_headers(
        client,
        email="compatibility_user@example.com",
        fingerprint="compat-current-device",
        user_agent="pytest-browser-current",
        forwarded_for="10.0.1.8",
    )

    target_session = next(
        session
        for session in fake_db.user_sessions.items
        if session.get("fingerprint") != fake_db.user_sessions.items[-1].get("fingerprint")
    )
    response = client.post(
        "/api/v1/auth/account/logout-session",
        json={"session_id": str(target_session["_id"])},
        headers=current_headers,
    )

    assert response.status_code == 200
    assert response.json()["success"] is True
    assert target_session["revoked_at"] is not None


def test_session_termination_rejects_invalid_foreign_and_current_sessions() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Primary User",
            "email": "primary_session_user@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other User",
            "email": "other_session_user@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )

    _, current_headers = _login_with_headers(
        client,
        email="primary_session_user@example.com",
        fingerprint="primary-current-device",
        user_agent="pytest-primary-current",
        forwarded_for="10.0.2.8",
    )
    _login_with_headers(
        client,
        email="other_session_user@example.com",
        fingerprint="other-user-device",
        user_agent="pytest-other-user",
        forwarded_for="10.0.2.9",
    )

    invalid = client.post("/api/v1/auth/sessions/not-a-real-id/terminate", headers=current_headers)
    assert invalid.status_code == 404

    own_current_session = next(
        session
        for session in fake_db.user_sessions.items
        if session.get("user_id") == str(fake_db.users.items[0]["_id"])
    )
    current = client.post(
        f"/api/v1/auth/sessions/{own_current_session['_id']}/terminate",
        headers=current_headers,
    )
    assert current.status_code == 400
    assert "logout" in current.json()["detail"].lower()

    foreign_session = next(
        session
        for session in fake_db.user_sessions.items
        if session.get("user_id") == str(fake_db.users.items[1]["_id"])
    )
    foreign = client.post(
        f"/api/v1/auth/sessions/{foreign_session['_id']}/terminate",
        headers=current_headers,
    )
    assert foreign.status_code == 403


def test_security_toggle_sms_not_enrolled_returns_400() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "SMS Toggle User",
            "email": "sms_toggle@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "sms_toggle@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    toggle_sms = client.post(
        "/api/v1/auth/security-settings/me/mfa/toggle",
        json={"method": "sms"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert toggle_sms.status_code == 400
    assert "not enabled" in str(toggle_sms.json().get("detail", "")).lower()


def test_sms_enrollment_wrong_code_and_expiry_fail_cleanly() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    _, auth_headers = _register_and_login(
        client,
        full_name="SMS Expiry User",
        email="sms_expiry@example.com",
        role="teacher",
    )

    send_enroll = client.post(
        "/api/v1/auth/mfa/sms/enroll/send",
        json={"phone_number": "+15551234567"},
        headers=auth_headers,
    )
    assert send_enroll.status_code == 200

    wrong_code = client.post(
        "/api/v1/auth/mfa/sms/enroll/verify",
        json={"otp_code": "000000"},
        headers=auth_headers,
    )
    assert wrong_code.status_code == 401
    assert "invalid sms verification code" in wrong_code.json()["detail"].lower()

    fake_db.users.items[0]["mfa_sms_enroll_otp_expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = client.post(
        "/api/v1/auth/mfa/sms/enroll/verify",
        json={"otp_code": send_enroll.json()["otp_dev"]},
        headers=auth_headers,
    )
    assert expired.status_code == 401
    assert "expired" in expired.json()["detail"].lower()


def test_sms_enrollment_enforces_attempt_cap() -> None:
    _setup_fake_db()
    client = TestClient(app)

    _, auth_headers = _register_and_login(
        client,
        full_name="SMS Attempts User",
        email="sms_attempts@example.com",
        role="teacher",
    )

    send_enroll = client.post(
        "/api/v1/auth/mfa/sms/enroll/send",
        json={"phone_number": "+15551234567"},
        headers=auth_headers,
    )
    assert send_enroll.status_code == 200

    for _ in range(settings.mfa_sms_verify_max_attempts):
        attempt = client.post(
            "/api/v1/auth/mfa/sms/enroll/verify",
            json={"otp_code": "111111"},
            headers=auth_headers,
        )
        assert attempt.status_code == 401

    capped = client.post(
        "/api/v1/auth/mfa/sms/enroll/verify",
        json={"otp_code": send_enroll.json()["otp_dev"]},
        headers=auth_headers,
    )
    assert capped.status_code == 429
    assert "maximum sms verification attempts" in capped.json()["detail"].lower()


def test_sms_login_challenge_resend_and_verify() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    _, auth_headers = _register_and_login(
        client,
        full_name="SMS Resend User",
        email="sms_resend@example.com",
        role="teacher",
    )

    send_enroll = client.post(
        "/api/v1/auth/mfa/sms/enroll/send",
        json={"phone_number": "+15551234567"},
        headers=auth_headers,
    )
    verify_enroll = client.post(
        "/api/v1/auth/mfa/sms/enroll/verify",
        json={"otp_code": send_enroll.json()["otp_dev"]},
        headers=auth_headers,
    )
    assert verify_enroll.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "sms_resend@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    pending_payload = login.json()
    user = fake_db.users.items[0]
    user["mfa_sms_login_last_sent_at"] = datetime.now(timezone.utc) - timedelta(
        seconds=settings.mfa_sms_send_min_interval_seconds + 1
    )

    resend = client.post(
        "/api/v1/auth/mfa/sms/challenge/resend",
        json={"pending_mfa_token": pending_payload["pending_mfa_token"]},
    )
    assert resend.status_code == 200
    resend_payload = resend.json()
    assert resend_payload["resend"] is True
    assert resend_payload["otp_dev"]

    verify_login = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "pending_mfa_token": pending_payload["pending_mfa_token"],
            "mfa_method": "sms",
            "mfa_code": resend_payload["otp_dev"],
        },
    )
    assert verify_login.status_code == 200
    assert verify_login.json()["access_token"]


def test_invalid_and_expired_pending_mfa_tokens_are_rejected() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    _, auth_headers = _register_and_login(
        client,
        full_name="Pending MFA User",
        email="pending_mfa@example.com",
        role="teacher",
    )

    enable_totp = client.post("/api/v1/auth/mfa/totp/enable", headers=auth_headers)
    secret = enable_totp.json()["secret"]
    confirm_totp = client.post(
        "/api/v1/auth/mfa/totp/confirm",
        json={"otp_code": pyotp.TOTP(secret).now()},
        headers=auth_headers,
    )
    assert confirm_totp.status_code == 200

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "pending_mfa@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    pending_payload = login.json()

    invalid = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "pending_mfa_token": "not-a-valid-token",
            "mfa_method": "totp",
            "mfa_code": "123456",
        },
    )
    assert invalid.status_code == 401

    fake_db.users.items[0]["mfa_pending_login"]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=1)
    expired = client.post(
        "/api/v1/auth/mfa/verify",
        json={
            "pending_mfa_token": pending_payload["pending_mfa_token"],
            "mfa_method": "totp",
            "mfa_code": pyotp.TOTP(secret).now(),
        },
    )
    assert expired.status_code == 401
    assert "expired" in expired.json()["detail"].lower()


def test_sms_enrollment_returns_controlled_error_when_twilio_is_not_configured(monkeypatch) -> None:
    _setup_fake_db()
    client = TestClient(app)

    _, auth_headers = _register_and_login(
        client,
        full_name="SMS Production User",
        email="sms_production@example.com",
        role="teacher",
    )

    monkeypatch.setattr(settings, "environment", "production")
    monkeypatch.setattr(settings, "sms_mfa_enabled", True)
    monkeypatch.setattr(settings, "twilio_account_sid", "")
    monkeypatch.setattr(settings, "twilio_auth_token", "")
    monkeypatch.setattr(settings, "twilio_from_number", "")
    monkeypatch.setattr(settings, "twilio_messaging_service_sid", "")
    monkeypatch.setattr(auth_service_module, "TwilioClient", None)

    response = client.post(
        "/api/v1/auth/mfa/sms/enroll/send",
        json={"phone_number": "+15551234567"},
        headers=auth_headers,
    )
    assert response.status_code == 503
    assert "not configured" in response.json()["detail"].lower()


def test_webauthn_registration_begin_and_finish(monkeypatch) -> None:
    _setup_fake_db()
    client = TestClient(app)
    _install_webauthn_test_mocks(monkeypatch)

    _, auth_headers = _register_and_login(
        client,
        full_name="WebAuthn Register User",
        email="webauthn_register@example.com",
        role="teacher",
    )

    begin = client.post(
        "/api/v1/auth/mfa/webauthn/register/begin",
        json={"label": "Work laptop"},
        headers=auth_headers,
    )
    assert begin.status_code == 200
    assert begin.json()["options"]["challenge"] == "registration-challenge"

    finish = client.post(
        "/api/v1/auth/mfa/webauthn/register/finish",
        json={
          "label": "Work laptop",
          "credential": {
              "id": "credential-1",
              "response": {
                  "clientDataJSON": _build_webauthn_client_data("http://localhost:5173"),
                  "transports": ["usb"],
              },
          },
        },
        headers=auth_headers,
    )
    assert finish.status_code == 200
    payload = finish.json()
    assert payload["success"] is True
    assert payload["credential_id"] == auth_service_module.AuthService._b64url_encode(b"credential-1")


def test_webauthn_registration_rejects_invalid_origin(monkeypatch) -> None:
    _setup_fake_db()
    client = TestClient(app)
    _install_webauthn_test_mocks(monkeypatch)

    _, auth_headers = _register_and_login(
        client,
        full_name="WebAuthn Origin User",
        email="webauthn_origin@example.com",
        role="teacher",
    )

    begin = client.post(
        "/api/v1/auth/mfa/webauthn/register/begin",
        json={"label": "Security key"},
        headers=auth_headers,
    )
    assert begin.status_code == 200

    finish = client.post(
        "/api/v1/auth/mfa/webauthn/register/finish",
        json={
            "credential": {
                "id": "credential-1",
                "response": {
                    "clientDataJSON": _build_webauthn_client_data("https://evil.example"),
                },
            }
        },
        headers=auth_headers,
    )
    assert finish.status_code == 400
    assert "origin is not allowed" in finish.json()["detail"].lower()


def test_webauthn_authentication_begin_and_finish(monkeypatch) -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    _install_webauthn_test_mocks(monkeypatch, authentication_sign_count=4)

    _, auth_headers = _register_and_login(
        client,
        full_name="WebAuthn Login User",
        email="webauthn_login@example.com",
        role="teacher",
    )

    user = fake_db.users.items[0]
    user["mfa_webauthn_enabled"] = True
    user["mfa_webauthn_credentials"] = [
        {
            "credential_id": "credential-1",
            "public_key": "public-key-1",
            "sign_count": 1,
            "label": "Security Key",
            "transports": ["usb"],
        }
    ]
    user["mfa_primary_method"] = "webauthn"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "webauthn_login@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    pending_payload = login.json()

    begin = client.post(
        "/api/v1/auth/mfa/webauthn/authenticate/begin",
        json={"pending_mfa_token": pending_payload["pending_mfa_token"]},
    )
    assert begin.status_code == 200
    assert begin.json()["options"]["challenge"] == "authentication-challenge"

    finish = client.post(
        "/api/v1/auth/mfa/webauthn/authenticate/finish",
        json={
            "pending_mfa_token": pending_payload["pending_mfa_token"],
            "credential": {
                "id": "credential-1",
                "response": {
                    "clientDataJSON": _build_webauthn_client_data("http://localhost:5173"),
                },
            },
        },
    )
    assert finish.status_code == 200
    assert finish.json()["access_token"]
    assert user["mfa_webauthn_credentials"][0]["sign_count"] == 4


def test_webauthn_authentication_rejects_unknown_credential(monkeypatch) -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    _install_webauthn_test_mocks(monkeypatch)

    _, auth_headers = _register_and_login(
        client,
        full_name="WebAuthn Unknown Credential User",
        email="webauthn_unknown@example.com",
        role="teacher",
    )

    user = fake_db.users.items[0]
    user["mfa_webauthn_enabled"] = True
    user["mfa_webauthn_credentials"] = [
        {
            "credential_id": "credential-1",
            "public_key": "public-key-1",
            "sign_count": 0,
            "label": "Security Key",
        }
    ]
    user["mfa_primary_method"] = "webauthn"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "webauthn_unknown@example.com", "password": "password123"},
    )
    pending_payload = login.json()
    begin = client.post(
        "/api/v1/auth/mfa/webauthn/authenticate/begin",
        json={"pending_mfa_token": pending_payload["pending_mfa_token"]},
    )
    assert begin.status_code == 200

    finish = client.post(
        "/api/v1/auth/mfa/webauthn/authenticate/finish",
        json={
            "pending_mfa_token": pending_payload["pending_mfa_token"],
            "credential": {
                "id": "credential-unknown",
                "response": {
                    "clientDataJSON": _build_webauthn_client_data("http://localhost:5173"),
                },
            },
        },
    )
    assert finish.status_code == 401
    assert "unknown webauthn credential" in finish.json()["detail"].lower()


def test_webauthn_authentication_rejects_invalid_challenge(monkeypatch) -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)
    _install_webauthn_test_mocks(monkeypatch)
    monkeypatch.setattr(
        auth_service_module,
        "verify_authentication_response",
        lambda **kwargs: (_ for _ in ()).throw(Exception("bad challenge")),
        raising=False,
    )

    _, auth_headers = _register_and_login(
        client,
        full_name="WebAuthn Challenge User",
        email="webauthn_challenge@example.com",
        role="teacher",
    )

    user = fake_db.users.items[0]
    user["mfa_webauthn_enabled"] = True
    user["mfa_webauthn_credentials"] = [
        {
            "credential_id": "credential-1",
            "public_key": "public-key-1",
            "sign_count": 0,
            "label": "Security Key",
        }
    ]
    user["mfa_primary_method"] = "webauthn"

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "webauthn_challenge@example.com", "password": "password123"},
    )
    pending_payload = login.json()
    begin = client.post(
        "/api/v1/auth/mfa/webauthn/authenticate/begin",
        json={"pending_mfa_token": pending_payload["pending_mfa_token"]},
    )
    assert begin.status_code == 200

    finish = client.post(
        "/api/v1/auth/mfa/webauthn/authenticate/finish",
        json={
            "pending_mfa_token": pending_payload["pending_mfa_token"],
            "credential": {
                "id": "credential-1",
                "response": {
                    "clientDataJSON": _build_webauthn_client_data("http://localhost:5173"),
                },
            },
        },
    )
    assert finish.status_code == 401
    assert "verification failed" in finish.json()["detail"].lower()


def test_users_endpoint_allows_custom_rbac_admin_types_in_response() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Super Admin",
            "email": "superadmin_users_scope@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert register.status_code == 201

    fake_db.users.items.append(
        {
            "_id": ObjectId(),
            "full_name": "Scoped Report Reviewer",
            "email": "reviewer_scope@example.com",
            "hashed_password": "unused",
            "role": "admin",
            "admin_type": "report_reviewer",
            "extended_roles": [],
            "role_scope": {},
            "is_active": True,
            "must_change_password": False,
        }
    )

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "superadmin_users_scope@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]

    users = client.get("/api/v1/users/", headers={"Authorization": f"Bearer {token}"})
    assert users.status_code == 200
    payload = users.json()
    assert any(item["admin_type"] == "report_reviewer" for item in payload)


def test_blacklist_jti_ignores_duplicate_insert_race() -> None:
    class DuplicateOnceCollection:
        def __init__(self) -> None:
            self.find_calls = 0
            self.insert_calls = 0

        async def find_one(self, query: Dict[str, Any]) -> Dict[str, Any] | None:
            _ = query
            self.find_calls += 1
            return None

        async def insert_one(self, document: Dict[str, Any]):
            self.insert_calls += 1
            raise DuplicateKeyError(
                "duplicate key",
                11000,
                {"errmsg": "duplicate key", "keyPattern": {"jti": 1}, "keyValue": {"jti": document["jti"]}},
            )

    collection = DuplicateOnceCollection()
    repository = AuthRepository(
        db_provider=lambda: type("DbStub", (), {"token_blacklist": collection})()
    )

    asyncio.run(
        repository.blacklist_jti(
            {
                "jti": "race-jti",
                "token_type": "refresh",
                "user_id": str(ObjectId()),
                "blacklisted_at": datetime.now(timezone.utc),
                "expires_at": datetime.now(timezone.utc),
            }
        )
    )

    assert collection.find_calls == 1
    assert collection.insert_calls == 1


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


def test_student_registration_creates_academic_student_profile() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin_student_sync@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin_register.status_code == 201

    student_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Sync",
            "email": "student_sync@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert student_register.status_code == 201

    assert len(fake_db.students.items) == 1
    created_profile = fake_db.students.items[0]
    assert created_profile["email"] == "student_sync@example.com"
    assert created_profile["full_name"] == "Student Sync"
    assert created_profile["user_id"] == student_register.json()["id"]
    assert created_profile["roll_number"].startswith("USR-")

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_student_sync@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    students = client.get("/api/v1/students/", headers=admin_headers)
    assert students.status_code == 200
    assert len(students.json()) == 1
    assert students.json()[0]["email"] == "student_sync@example.com"


def test_admin_user_creation_creates_academic_student_profile() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin_register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin User",
            "email": "admin_user_create_sync@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin_register.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_user_create_sync@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    created_user = client.post(
        "/api/v1/users/",
        json={
            "full_name": "Student Created By Admin",
            "email": "student_created_by_admin@example.com",
            "password": "password123",
            "role": "student",
        },
        headers=admin_headers,
    )
    assert created_user.status_code == 201

    assert len(fake_db.students.items) == 1
    created_profile = fake_db.students.items[0]
    assert created_profile["email"] == "student_created_by_admin@example.com"
    assert created_profile["user_id"] == created_user.json()["id"]


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


def test_admin_can_create_canonical_sections() -> None:
    fake_db = _setup_fake_db()
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
    structure = _seed_canonical_structure(fake_db, suffix="ADM6")

    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="BCA FY"),
        headers=headers,
    )
    assert class_item.status_code == 201


def test_legacy_course_api_is_removed() -> None:
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
    assert course.status_code == 404


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


def test_legacy_year_api_is_removed() -> None:
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
    assert create.status_code == 404


def test_program_and_subject_code_must_be_unique() -> None:
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
    faculty = client.post(
        "/api/v1/faculties/",
        json={"name": "Faculty Unique", "code": "FACUNI"},
        headers=headers,
    )
    assert faculty.status_code == 201
    department = client.post(
        "/api/v1/departments/",
        json={"name": "Department Unique", "code": "DEPUNI", "faculty_id": faculty.json()["id"]},
        headers=headers,
    )
    assert department.status_code == 201

    first_program = client.post(
        "/api/v1/programs/",
        json={"name": "Program A", "code": "CSE101", "department_id": department.json()["id"], "duration_years": 4},
        headers=headers,
    )
    assert first_program.status_code == 201
    duplicate_program = client.post(
        "/api/v1/programs/",
        json={"name": "Program B", "code": "cse101", "department_id": department.json()["id"], "duration_years": 4},
        headers=headers,
    )
    assert duplicate_program.status_code == 400
    assert duplicate_program.json()["detail"] == "Program code already exists"

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


def test_class_create_requires_matching_batch_and_program() -> None:
    fake_db = _setup_fake_db()
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
    structure_one = _seed_canonical_structure(fake_db, suffix="CO1")
    structure_two = _seed_canonical_structure(fake_db, suffix="CO2")

    mismatch = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure_two,
            name="Invalid Class",
            batch_id=str(structure_one["batch_id"]),
        ),
        headers=headers,
    )
    assert mismatch.status_code == 400
    assert mismatch.json()["detail"] == "batch_id does not belong to provided program_id"


def test_student_create_requires_valid_class_and_unique_roll_number() -> None:
    fake_db = _setup_fake_db()
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

    structure = _seed_canonical_structure(fake_db, suffix="STU1")
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="BCA Y1"),
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
    fake_db = _setup_fake_db()
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
    structure = _seed_canonical_structure(fake_db, suffix="ENR1")
    class_one = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="Class One",
            class_coordinator_user_id=teacher_one.json()["id"],
        ),
        headers=admin_headers,
    )
    class_two = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="Class Two",
            class_coordinator_user_id=teacher_two.json()["id"],
        ),
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
    fake_db = _setup_fake_db()
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
    structure = _seed_canonical_structure(fake_db, suffix="YHEN")
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="General Class",
            class_coordinator_user_id=coordinator.json()["id"],
        ),
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


def test_registration_is_closed_after_first_admin() -> None:
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
    assert second_admin.json()["detail"] == "Self-registration is closed. Contact super admin."


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
    fake_db = _setup_fake_db()
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
    structure = _seed_canonical_structure(fake_db, suffix="E302")
    class_one = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="Class One",
            class_coordinator_user_id=coordinator_one.json()["id"],
        ),
        headers=admin_headers,
    )
    class_two = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="Class Two",
            class_coordinator_user_id=coordinator_two.json()["id"],
        ),
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


def test_students_receive_scoped_notices_for_their_class_batch_and_subject() -> None:
    fake_db = _setup_fake_db()
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
    structure = _seed_canonical_structure(fake_db, suffix="NTSC", start_year=2023, semester_number=3)
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="BTech Y2 A"),
        headers=admin_headers,
    )
    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Data Structures", "code": "DS-NOT", "description": "desc"},
        headers=admin_headers,
    )
    student_profile = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Student",
            "roll_number": "R-NOT-1",
            "email": "student_notice_scope@example.com",
            "class_id": class_item.json()["id"],
        },
        headers=admin_headers,
    )
    assignment = client.post(
        "/api/v1/assignments/",
        json={
            "title": "Notice Scope Assignment",
            "description": "desc",
            "class_id": class_item.json()["id"],
            "subject_id": subject.json()["id"],
            "total_marks": 100,
        },
        headers=admin_headers,
    )
    assert class_item.status_code == 201
    assert subject.status_code == 201
    assert student_profile.status_code == 201
    assert assignment.status_code == 201

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
            "scope_ref_id": class_item.json()["id"],
        },
        headers=admin_headers,
    )
    batch_notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "Batch Internal",
            "message": "Batch-only announcement",
            "priority": "normal",
            "scope": "batch",
            "scope_ref_id": str(structure["batch_id"]),
        },
        headers=admin_headers,
    )
    subject_notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "Subject Internal",
            "message": "Subject-only announcement",
            "priority": "normal",
            "scope": "subject",
            "scope_ref_id": subject.json()["id"],
        },
        headers=admin_headers,
    )
    assert college_notice.status_code == 201
    assert class_notice.status_code == 201
    assert batch_notice.status_code == 201
    assert subject_notice.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_notice_scope@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    listed = client.get("/api/v1/notices/", headers=student_headers)
    assert listed.status_code == 200
    body = listed.json()
    titles = {item["title"] for item in body}
    assert "Campus Update" in titles
    assert "Class Internal" in titles
    assert "Batch Internal" in titles
    assert "Subject Internal" in titles


def test_student_can_mark_visible_notice_read_and_unread_count_updates() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_notice_read@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student",
            "email": "student_notice_read@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_notice_read@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    structure = _seed_canonical_structure(fake_db, suffix="NRDC", start_year=2023, semester_number=3)
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Notice Read Section"),
        headers=admin_headers,
    )
    assert class_item.status_code == 201

    student_profile = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Student",
            "roll_number": "R-NRDC-1",
            "email": "student_notice_read@example.com",
            "class_id": class_item.json()["id"],
        },
        headers=admin_headers,
    )
    assert student_profile.status_code == 201

    notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "Visible Notice",
            "message": "Read me",
            "priority": "normal",
            "scope": "class",
            "scope_ref_id": class_item.json()["id"],
        },
        headers=admin_headers,
    )
    assert notice.status_code == 201

    hidden_subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Hidden Subject", "code": "NRDC-HID", "description": "hidden"},
        headers=admin_headers,
    )
    assert hidden_subject.status_code == 201

    hidden_notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "Hidden Notice",
            "message": "Do not count me",
            "priority": "normal",
            "scope": "subject",
            "scope_ref_id": hidden_subject.json()["id"],
        },
        headers=admin_headers,
    )
    assert hidden_notice.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_notice_read@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    unread_before = client.get("/api/v1/notices/unread-count", headers=student_headers)
    assert unread_before.status_code == 200
    assert unread_before.json() == {"count": 1}

    listed_before = client.get("/api/v1/notices/", headers=student_headers)
    assert listed_before.status_code == 200
    visible_notice = next(item for item in listed_before.json() if item["title"] == "Visible Notice")
    assert visible_notice["is_read"] is False

    marked = client.post(f"/api/v1/notices/{visible_notice['id']}/read", headers=student_headers)
    assert marked.status_code == 200
    assert marked.json()["is_read"] is True
    assert marked.json()["read_count"] == 1

    unread_after = client.get("/api/v1/notices/unread-count", headers=student_headers)
    assert unread_after.status_code == 200
    assert unread_after.json() == {"count": 0}


def test_student_dashboard_endpoint_consolidates_summary_notices_deadlines_and_timetable() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_dashboard_student@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student",
            "email": "student_dashboard_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_dashboard_student@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_dashboard_student@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    student_user_id = student_login.json()["user"]["id"]

    structure = _seed_canonical_structure(fake_db, suffix="DSHB", start_year=2023, semester_number=5)
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Dashboard Section"),
        headers=admin_headers,
    )
    assert class_item.status_code == 201

    student_profile = client.post(
        "/api/v1/students/",
        json={
            "full_name": "Dashboard Student",
            "roll_number": "R-DSHB-1",
            "email": "student_dashboard_student@example.com",
            "class_id": class_item.json()["id"],
        },
        headers=admin_headers,
    )
    assert student_profile.status_code == 201

    subject = client.post(
        "/api/v1/subjects/",
        json={"name": "Algorithms", "code": "ALGO-DSHB", "description": "Algorithms"},
        headers=admin_headers,
    )
    assert subject.status_code == 201

    assignment = client.post(
        "/api/v1/assignments/",
        json={
            "title": "Dashboard Assignment",
            "description": "Assignment for dashboard",
            "class_id": class_item.json()["id"],
            "subject_id": subject.json()["id"],
            "total_marks": 100,
            "due_date": "2030-01-01T10:00:00+00:00",
        },
        headers=admin_headers,
    )
    assert assignment.status_code == 201

    fake_db.submissions.items.append(
        {
            "_id": ObjectId(),
            "assignment_id": assignment.json()["id"],
            "student_user_id": student_user_id,
            "status": "submitted",
        }
    )
    fake_db.evaluations.items.append(
        {
            "_id": ObjectId(),
            "student_user_id": student_user_id,
        }
    )
    fake_db.notices.items.append(
        {
            "_id": ObjectId(),
            "title": "Urgent Dashboard Notice",
            "message": "Read this now",
            "priority": "urgent",
            "scope": "class",
            "scope_ref_id": class_item.json()["id"],
            "expires_at": None,
            "images": [],
            "is_pinned": False,
            "scheduled_at": None,
            "read_count": 0,
            "seen_by": [],
            "created_by": admin.json()["id"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    )

    offering_id = ObjectId()
    fake_db.course_offerings.items.append(
        {
            "_id": offering_id,
            "subject_id": subject.json()["id"],
            "teacher_user_id": admin.json()["id"],
            "section_id": class_item.json()["id"],
            "group_id": None,
            "offering_type": "theory",
            "is_active": True,
        }
    )
    fake_db.class_slots.items.append(
        {
            "_id": ObjectId(),
            "course_offering_id": str(offering_id),
            "day": "Monday",
            "start_time": "09:00",
            "end_time": "10:00",
            "room_code": "A-101",
            "is_active": True,
        }
    )
    fake_db.internship_sessions.items.append(
        {
            "_id": ObjectId(),
            "student_user_id": student_user_id,
            "student_id": student_profile.json()["id"],
            "status": "active",
            "clock_in_at": datetime.now(timezone.utc),
            "clock_out_at": None,
            "total_minutes": None,
            "auto_closed": False,
            "note": "Active internship",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "schema_version": 1,
        }
    )

    dashboard = client.get("/api/v1/analytics/dashboard", headers=student_headers)
    assert dashboard.status_code == 200, dashboard.text
    body = dashboard.json()
    assert body["summary"]["total_submissions"] == 1
    assert body["summary"]["total_evaluations"] == 1
    assert body["summary"]["pending_reviews"] == 1
    assert len(body["urgent_notices"]) == 1
    assert body["urgent_notices"][0]["title"] == "Urgent Dashboard Notice"
    assert len(body["student_dashboard"]["deadlines"]) == 1
    assert body["student_dashboard"]["deadlines"][0]["title"] == "Dashboard Assignment"
    assert len(body["student_dashboard"]["timetable"]) == 1
    assert body["student_dashboard"]["timetable"][0]["sessions"][0]["subject"] == "Algorithms"
    assert body["student_dashboard"]["internship_status"]["status"] == "active"


def test_session_bootstrap_consolidates_user_notice_count_and_branding() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Bootstrap Admin",
            "email": "bootstrap_admin@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Bootstrap Student",
            "email": "bootstrap_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "bootstrap_admin@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "bootstrap_student@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}

    structure = _seed_canonical_structure(fake_db, suffix="BOOT", semester_number=2)
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Bootstrap Section"),
        headers=admin_headers,
    )
    assert class_item.status_code == 201

    fake_db.students.items.append(
        {
            "_id": ObjectId(),
            "full_name": "Bootstrap Student",
            "roll_number": "BOOT-1",
            "email": "bootstrap_student@example.com",
            "class_id": class_item.json()["id"],
            "is_active": True,
        }
    )

    fake_db.notices.items.append(
        {
            "_id": ObjectId(),
            "title": "Bootstrap Notice",
            "message": "Visible in bootstrap",
            "priority": "normal",
            "scope": "class",
            "scope_ref_id": class_item.json()["id"],
            "expires_at": None,
            "images": [],
            "is_pinned": False,
            "scheduled_at": None,
            "read_count": 0,
            "seen_by": [],
            "created_by": admin.json()["id"],
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    )
    fake_db.notifications.items.append(
        {
            "_id": ObjectId(),
            "title": "Bootstrap Notification",
            "message": "Visible notification badge",
            "priority": "normal",
            "scope": "global",
            "target_user_id": student.json()["id"],
            "created_by": admin.json()["id"],
            "is_read": False,
            "created_at": datetime.now(timezone.utc),
        }
    )
    fake_db.settings.items.append(
        {
            "_id": ObjectId(),
            "key": "branding_logo",
            "filename": "logo.png",
            "updated_at": datetime(2030, 1, 1, tzinfo=timezone.utc),
        }
    )

    original_logo_file_path_async = branding_endpoint._logo_file_path_async

    async def fake_logo_file_path_async():
        return branding_endpoint.BRANDING_DIR / "logo.png"

    branding_endpoint._logo_file_path_async = fake_logo_file_path_async
    try:
        bootstrap = client.get("/api/v1/session/bootstrap", headers=student_headers)
        assert bootstrap.status_code == 200, bootstrap.text
        body = bootstrap.json()
        assert body["user"]["email"] == "bootstrap_student@example.com"
        assert body["unread_notice_count"] == 1
        assert body["unread_notification_count"] == 1
        assert body["branding"]["has_logo"] is True
        assert body["branding"]["filename"] == "logo.png"
        assert body["generated_at"]
    finally:
        branding_endpoint._logo_file_path_async = original_logo_file_path_async


def test_profile_update_persists_communication_preferences_and_bootstrap_returns_them() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Preference Student",
            "email": "preference_student@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "preference_student@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    updated = client.patch(
        "/api/v1/auth/profile",
        json={
            "city": "Indore",
            "communication_preferences": {
                "announcement_email": False,
                "club_announcement_email": True,
                "notification_email": False,
            },
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["profile"]["city"] == "Indore"
    assert body["communication_preferences"]["announcement_email"] is False
    assert body["communication_preferences"]["club_announcement_email"] is True
    assert body["communication_preferences"]["notification_email"] is False

    bootstrap = client.get("/api/v1/session/bootstrap", headers=headers)
    assert bootstrap.status_code == 200, bootstrap.text
    bootstrap_body = bootstrap.json()
    assert bootstrap_body["user"]["communication_preferences"]["announcement_email"] is False
    assert bootstrap_body["user"]["communication_preferences"]["club_announcement_email"] is True
    assert bootstrap_body["user"]["communication_preferences"]["notification_email"] is False


def test_dedicated_communication_preferences_endpoint_updates_and_reads_preferences() -> None:
    _setup_fake_db()
    client = TestClient(app)

    register = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Prefs Endpoint User",
            "email": "prefs_endpoint_user@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert register.status_code == 201

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "prefs_endpoint_user@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    current = client.get("/api/v1/auth/communication-preferences", headers=headers)
    assert current.status_code == 200, current.text
    current_body = current.json()
    assert current_body["announcement_email"] is True
    assert current_body["club_announcement_email"] is True
    assert current_body["notification_email"] is True
    assert current_body["notification_in_app"] is True
    assert current_body["notification_email_mode"] == "instant"
    assert current_body["notification_scope_preferences"]["system"]["email_mode"] == "inherit"
    assert current_body["digest_preferences"]["daily_digest_hour_utc"] == 8

    updated = client.patch(
        "/api/v1/auth/communication-preferences",
        json={
            "announcement_email": False,
            "club_announcement_email": False,
            "notification_email_mode": "daily_digest",
            "notification_scope_preferences": {
                "system": {"in_app": False, "email_mode": "off"},
                "ai": {"email_mode": "weekly_digest"},
            },
            "digest_preferences": {
                "daily_digest_hour_utc": 18,
                "weekly_digest_day_of_week": 4,
            },
        },
        headers=headers,
    )
    assert updated.status_code == 200, updated.text
    updated_body = updated.json()
    assert updated_body["announcement_email"] is False
    assert updated_body["club_announcement_email"] is False
    assert updated_body["notification_email"] is True
    assert updated_body["notification_in_app"] is True
    assert updated_body["notification_email_mode"] == "daily_digest"
    assert updated_body["notification_scope_preferences"]["system"]["in_app"] is False
    assert updated_body["notification_scope_preferences"]["system"]["email_mode"] == "off"
    assert updated_body["notification_scope_preferences"]["ai"]["email_mode"] == "weekly_digest"
    assert updated_body["digest_preferences"]["daily_digest_hour_utc"] == 18
    assert updated_body["digest_preferences"]["weekly_digest_day_of_week"] == 4

    partial = client.patch(
        "/api/v1/auth/communication-preferences",
        json={
            "notification_scope_preferences": {
                "system": {"email_mode": "instant"},
            }
        },
        headers=headers,
    )
    assert partial.status_code == 200, partial.text
    partial_body = partial.json()
    assert partial_body["notification_scope_preferences"]["system"]["in_app"] is False
    assert partial_body["notification_scope_preferences"]["system"]["email_mode"] == "instant"
    assert partial_body["digest_preferences"]["daily_digest_hour_utc"] == 18

    reloaded = client.get("/api/v1/auth/communication-preferences", headers=headers)
    assert reloaded.status_code == 200, reloaded.text
    reloaded_body = reloaded.json()
    assert reloaded_body["announcement_email"] is False
    assert reloaded_body["club_announcement_email"] is False
    assert reloaded_body["notification_email"] is True
    assert reloaded_body["notification_email_mode"] == "daily_digest"
    assert reloaded_body["notification_scope_preferences"]["system"]["in_app"] is False
    assert reloaded_body["notification_scope_preferences"]["system"]["email_mode"] == "instant"
    assert reloaded_body["notification_scope_preferences"]["ai"]["email_mode"] == "weekly_digest"
    assert reloaded_body["digest_preferences"]["daily_digest_hour_utc"] == 18


def test_auth_me_skips_response_envelope_for_hot_path() -> None:
    _setup_fake_db()
    client = TestClient(app)

    original_enabled = settings.response_envelope_enabled
    original_skip_paths = list(settings.response_envelope_skip_paths)
    settings.response_envelope_enabled = True
    settings.response_envelope_skip_paths = ["/api/v1/auth/me"]
    try:
        register = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Envelope Admin",
                "email": "envelope_admin@example.com",
                "password": "password123",
                "role": "admin",
            },
        )
        assert register.status_code == 201

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "envelope_admin@example.com", "password": "password123"},
        )
        login_body = login.json()
        access_token = login_body.get("access_token") or login_body.get("data", {}).get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["email"] == "envelope_admin@example.com"
        assert "success" not in body
    finally:
        settings.response_envelope_enabled = original_enabled
        settings.response_envelope_skip_paths = original_skip_paths


def test_session_bootstrap_skips_response_envelope_for_hot_path() -> None:
    _setup_fake_db()
    client = TestClient(app)

    original_enabled = settings.response_envelope_enabled
    original_skip_paths = list(settings.response_envelope_skip_paths)
    settings.response_envelope_enabled = True
    settings.response_envelope_skip_paths = ["/api/v1/session/bootstrap"]
    try:
        register = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": "Bootstrap Envelope Admin",
                "email": "bootstrap_envelope_admin@example.com",
                "password": "password123",
                "role": "admin",
            },
        )
        assert register.status_code == 201

        login = client.post(
            "/api/v1/auth/login",
            json={"email": "bootstrap_envelope_admin@example.com", "password": "password123"},
        )
        login_body = login.json()
        access_token = login_body.get("access_token") or login_body.get("data", {}).get("access_token")
        headers = {"Authorization": f"Bearer {access_token}"}
        response = client.get("/api/v1/session/bootstrap", headers=headers)
        assert response.status_code == 200
        body = response.json()
        assert body["user"]["email"] == "bootstrap_envelope_admin@example.com"
        assert "success" not in body
    finally:
        settings.response_envelope_enabled = original_enabled
        settings.response_envelope_skip_paths = original_skip_paths


def test_teacher_cannot_read_other_teacher_class_by_id() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_class_read_scope@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    teacher_owner = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner Teacher",
            "email": "owner_class_read_scope@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    teacher_other = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other Teacher",
            "email": "other_class_read_scope@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert admin.status_code == 201
    assert teacher_owner.status_code == 201
    assert teacher_other.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_class_read_scope@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    structure = _seed_canonical_structure(fake_db, suffix="READ")
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="BTech Y1 A",
            class_coordinator_user_id=teacher_owner.json()["id"],
        ),
        headers=admin_headers,
    )
    assert class_item.status_code == 201

    owner_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner_class_read_scope@example.com", "password": "password123"},
    )
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    owner_get = client.get(f"/api/v1/sections/{class_item.json()['id']}", headers=owner_headers)
    assert owner_get.status_code == 200

    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": "other_class_read_scope@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}
    denied = client.get(f"/api/v1/sections/{class_item.json()['id']}", headers=other_headers)
    assert denied.status_code == 403
    assert denied.json()["detail"] == "Not allowed to view this class"


def test_teacher_notice_scope_requires_owned_class_and_valid_scope_ref() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_notice_validate@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Teacher Coordinator",
            "email": "teacher_notice_validate@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    other_teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Other Coordinator",
            "email": "other_teacher_notice_validate@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    assert admin.status_code == 201
    assert teacher.status_code == 201
    assert other_teacher.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_notice_validate@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    teacher_login = client.post(
        "/api/v1/auth/login",
        json={"email": "teacher_notice_validate@example.com", "password": "password123"},
    )
    teacher_headers = {"Authorization": f"Bearer {teacher_login.json()['access_token']}"}
    structure = _seed_canonical_structure(fake_db, suffix="NOTV")
    own_class = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="BCA FY A",
            class_coordinator_user_id=teacher.json()["id"],
        ),
        headers=admin_headers,
    )
    other_class = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="BCA FY B",
            class_coordinator_user_id=other_teacher.json()["id"],
        ),
        headers=admin_headers,
    )
    assert own_class.status_code == 201
    assert other_class.status_code == 201

    missing_ref = client.post(
        "/api/v1/notices/",
        json={
            "title": "Missing Ref",
            "message": "Invalid",
            "priority": "normal",
            "scope": "class",
        },
        headers=teacher_headers,
    )
    assert missing_ref.status_code == 400

    unauthorized_class = client.post(
        "/api/v1/notices/",
        json={
            "title": "Unauthorized",
            "message": "Invalid",
            "priority": "normal",
            "scope": "class",
            "scope_ref_id": other_class.json()["id"],
        },
        headers=teacher_headers,
    )
    assert unauthorized_class.status_code == 403

    allowed = client.post(
        "/api/v1/notices/",
        json={
            "title": "Allowed",
            "message": "Valid",
            "priority": "normal",
            "scope": "class",
            "scope_ref_id": own_class.json()["id"],
        },
        headers=teacher_headers,
    )
    assert allowed.status_code == 201


def test_teacher_submission_listing_applies_scope_before_pagination() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_submission_paging@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    teacher_owner = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner Teacher",
            "email": "owner_submission_paging@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    teacher_coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator Teacher",
            "email": "coord_submission_paging@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student",
            "email": "student_submission_paging@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert teacher_owner.status_code == 201
    assert teacher_coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_submission_paging@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    owner_login = client.post(
        "/api/v1/auth/login",
        json={"email": "owner_submission_paging@example.com", "password": "password123"},
    )
    owner_headers = {"Authorization": f"Bearer {owner_login.json()['access_token']}"}
    coord_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_submission_paging@example.com", "password": "password123"},
    )
    coord_headers = {"Authorization": f"Bearer {coord_login.json()['access_token']}"}
    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_submission_paging@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    structure = _seed_canonical_structure(fake_db, suffix="SPAG")
    class_one = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Class One"),
        headers=admin_headers,
    )
    class_two = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="Class Two",
            class_coordinator_user_id=teacher_coordinator.json()["id"],
        ),
        headers=admin_headers,
    )
    assert class_one.status_code == 201
    assert class_two.status_code == 201

    assignment_one = client.post(
        "/api/v1/assignments/",
        json={"title": "Out of Scope", "description": "desc", "class_id": class_one.json()["id"], "total_marks": 100},
        headers=owner_headers,
    )
    assignment_two = client.post(
        "/api/v1/assignments/",
        json={"title": "In Scope", "description": "desc", "class_id": class_two.json()["id"], "total_marks": 100},
        headers=owner_headers,
    )
    assert assignment_one.status_code == 201
    assert assignment_two.status_code == 201

    first_upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_one.json()["id"]},
        files={"file": ("one.txt", b"first", "text/plain")},
        headers=student_headers,
    )
    second_upload = client.post(
        "/api/v1/submissions/upload",
        data={"assignment_id": assignment_two.json()["id"]},
        files={"file": ("two.txt", b"second", "text/plain")},
        headers=student_headers,
    )
    assert first_upload.status_code == 201
    assert second_upload.status_code == 201

    listed = client.get("/api/v1/submissions/?skip=0&limit=1", headers=coord_headers)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["assignment_id"] == assignment_two.json()["id"]


def test_teacher_enrollment_listing_applies_scope_before_pagination() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_enrollment_paging@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_enrollment_paging@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["class_coordinator"],
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_enrollment_paging@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    coord_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_enrollment_paging@example.com", "password": "password123"},
    )
    coord_headers = {"Authorization": f"Bearer {coord_login.json()['access_token']}"}
    structure = _seed_canonical_structure(fake_db, suffix="ENPG")
    class_one = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(structure, name="Class One"),
        headers=admin_headers,
    )
    class_two = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure,
            name="Class Two",
            class_coordinator_user_id=coordinator.json()["id"],
        ),
        headers=admin_headers,
    )
    student_one = client.post(
        "/api/v1/students/",
        json={"full_name": "Student One", "roll_number": "ENR-1"},
        headers=admin_headers,
    )
    student_two = client.post(
        "/api/v1/students/",
        json={"full_name": "Student Two", "roll_number": "ENR-2"},
        headers=admin_headers,
    )
    assert class_one.status_code == 201
    assert class_two.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    add_one = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_one.json()["id"], "student_id": student_one.json()["id"]},
        headers=admin_headers,
    )
    add_two = client.post(
        "/api/v1/enrollments/",
        json={"class_id": class_two.json()["id"], "student_id": student_two.json()["id"]},
        headers=admin_headers,
    )
    assert add_one.status_code == 201
    assert add_two.status_code == 201

    listed = client.get("/api/v1/enrollments/?skip=0&limit=1", headers=coord_headers)
    assert listed.status_code == 200
    body = listed.json()
    assert len(body) == 1
    assert body[0]["class_id"] == class_two.json()["id"]


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


def test_unassigned_teacher_with_club_coordinator_extension_cannot_manage_other_club() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_scope_guard@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    owner = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Owner Coordinator",
            "email": "owner_club_scope_guard@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["club_coordinator"],
        },
    )
    other_teacher = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Unassigned Coordinator",
            "email": "other_club_scope_guard@example.com",
            "password": "password123",
            "role": "teacher",
            "extended_roles": ["club_coordinator"],
        },
    )
    assert admin.status_code == 201
    assert owner.status_code == 201
    assert other_teacher.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_scope_guard@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Security Club",
            "description": "Club",
            "coordinator_user_id": owner.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    other_login = client.post(
        "/api/v1/auth/login",
        json={"email": "other_club_scope_guard@example.com", "password": "password123"},
    )
    other_headers = {"Authorization": f"Bearer {other_login.json()['access_token']}"}

    denied_update = client.patch(
        f"/api/v1/clubs/{club.json()['id']}",
        json={"description": "Changed by wrong coordinator"},
        headers=other_headers,
    )
    assert denied_update.status_code == 403
    assert denied_update.json()["detail"] == "Not allowed to manage this club"

    denied_event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Unauthorized Event", "capacity": 20},
        headers=other_headers,
    )
    assert denied_event.status_code == 403
    assert denied_event.json()["detail"] == "Not allowed to manage this club event"


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


def test_members_only_event_is_visible_and_registerable_only_for_club_members() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_members_only_event@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Club Coordinator",
            "email": "coord_members_only_event@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    member_student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Club Member",
            "email": "member_members_only_event@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    outsider_student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Outsider Student",
            "email": "outsider_members_only_event@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert member_student.status_code == 201
    assert outsider_student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_members_only_event@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Robotics Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "open",
            "registration_open": True,
            "status": "active",
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_members_only_event@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Members Lab Session",
            "capacity": 20,
            "visibility": "members_only",
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    member_login = client.post(
        "/api/v1/auth/login",
        json={"email": "member_members_only_event@example.com", "password": "password123"},
    )
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}
    join = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=member_headers)
    assert join.status_code == 200

    visible_to_member = client.get(
        f"/api/v1/club-events/?club_id={club.json()['id']}",
        headers=member_headers,
    )
    assert visible_to_member.status_code == 200
    assert [row["id"] for row in visible_to_member.json()] == [event.json()["id"]]

    outsider_login = client.post(
        "/api/v1/auth/login",
        json={"email": "outsider_members_only_event@example.com", "password": "password123"},
    )
    outsider_headers = {"Authorization": f"Bearer {outsider_login.json()['access_token']}"}
    hidden_from_outsider = client.get(
        f"/api/v1/club-events/?club_id={club.json()['id']}",
        headers=outsider_headers,
    )
    assert hidden_from_outsider.status_code == 200
    assert hidden_from_outsider.json() == []

    denied_registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=outsider_headers,
    )
    assert denied_registration.status_code == 403
    assert denied_registration.json()["detail"] == "Only active club members can register for this event"

    allowed_registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=member_headers,
    )
    assert allowed_registration.status_code == 201


def test_club_application_approval_respects_capacity_limit() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_capacity_guard@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_capacity_guard@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_club_capacity_guard@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_club_capacity_guard@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_capacity_guard@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Design Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "approval_required",
            "registration_open": True,
            "status": "active",
            "max_members": 1,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_capacity_guard@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_club_capacity_guard@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    application_one = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_one_headers)
    assert application_one.status_code == 200
    assert application_one.json()["status"] == "pending"

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_club_capacity_guard@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    application_two = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_two_headers)
    assert application_two.status_code == 200
    assert application_two.json()["status"] == "pending"

    approved = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/applications/{application_one.json()['application_id']}",
        json={"status": "approved"},
        headers=coordinator_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    denied = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/applications/{application_two.json()['application_id']}",
        json={"status": "approved"},
        headers=coordinator_headers,
    )
    assert denied.status_code == 400
    assert denied.json()["detail"] == "Club membership capacity reached"

    applications = client.get(
        f"/api/v1/clubs/{club.json()['id']}/applications",
        headers=coordinator_headers,
    )
    assert applications.status_code == 200
    by_id = {item["id"]: item for item in applications.json()}
    assert by_id[application_two.json()["application_id"]]["status"] == "pending"


def test_open_club_full_capacity_adds_student_to_membership_waitlist() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_waitlist_open@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_waitlist_open@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_club_waitlist_open@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_club_waitlist_open@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_waitlist_open@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Capacity Open Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "open",
            "registration_open": True,
            "status": "active",
            "max_members": 1,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_club_waitlist_open@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    joined = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_one_headers)
    assert joined.status_code == 200
    assert joined.json()["status"] == "approved"

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_club_waitlist_open@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    waitlisted = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_two_headers)
    assert waitlisted.status_code == 200
    assert waitlisted.json()["status"] == "waitlisted"

    applications = client.get(
        f"/api/v1/clubs/{club.json()['id']}/applications",
        headers=admin_headers,
    )
    assert applications.status_code == 200
    assert len(applications.json()) == 1
    assert applications.json()[0]["status"] == "waitlisted"


def test_open_club_member_removal_promotes_oldest_waitlisted_application() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_waitlist_promote_open@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_waitlist_promote_open@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_club_waitlist_promote_open@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_club_waitlist_promote_open@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_waitlist_promote_open@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Promotion Open Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "open",
            "registration_open": True,
            "status": "active",
            "max_members": 1,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_club_waitlist_promote_open@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    joined = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_one_headers)
    assert joined.status_code == 200
    membership_id = joined.json()["membership_id"]

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_club_waitlist_promote_open@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    waitlisted = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_two_headers)
    assert waitlisted.status_code == 200
    assert waitlisted.json()["status"] == "waitlisted"

    removed = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/members/{membership_id}",
        json={"status": "removed"},
        headers=admin_headers,
    )
    assert removed.status_code == 200

    applications = client.get(
        f"/api/v1/clubs/{club.json()['id']}/applications",
        headers=admin_headers,
    )
    assert applications.status_code == 200
    assert applications.json()[0]["status"] == "approved"

    members = client.get(f"/api/v1/clubs/{club.json()['id']}/members", headers=admin_headers)
    assert members.status_code == 200
    by_email = {item["student_email"]: item for item in members.json()}
    assert by_email["student_one_club_waitlist_promote_open@example.com"]["status"] == "removed"
    assert by_email["student_two_club_waitlist_promote_open@example.com"]["status"] == "active"


def test_approval_required_club_waitlist_promotes_back_to_pending_when_seat_opens() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_waitlist_promote_pending@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_waitlist_promote_pending@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_club_waitlist_promote_pending@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_club_waitlist_promote_pending@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_waitlist_promote_pending@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Approval Queue Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "approval_required",
            "registration_open": True,
            "status": "active",
            "max_members": 1,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_waitlist_promote_pending@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_club_waitlist_promote_pending@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    application_one = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_one_headers)
    assert application_one.status_code == 200
    assert application_one.json()["status"] == "pending"

    approved = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/applications/{application_one.json()['application_id']}",
        json={"status": "approved"},
        headers=coordinator_headers,
    )
    assert approved.status_code == 200

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_club_waitlist_promote_pending@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    waitlisted = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_two_headers)
    assert waitlisted.status_code == 200
    assert waitlisted.json()["status"] == "waitlisted"

    members = client.get(f"/api/v1/clubs/{club.json()['id']}/members", headers=admin_headers)
    assert members.status_code == 200
    active_member = next(item for item in members.json() if item["status"] == "active")

    removed = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/members/{active_member['id']}",
        json={"status": "removed"},
        headers=admin_headers,
    )
    assert removed.status_code == 200

    applications = client.get(
        f"/api/v1/clubs/{club.json()['id']}/applications",
        headers=admin_headers,
    )
    assert applications.status_code == 200
    by_email = {item["student_email"]: item for item in applications.json()}
    assert by_email["student_two_club_waitlist_promote_pending@example.com"]["status"] == "pending"


def test_removed_member_can_rejoin_open_club_without_duplicate_membership() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_rejoin@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_rejoin@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Returning Student",
            "email": "student_club_rejoin@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_rejoin@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Photography Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "open",
            "registration_open": True,
            "status": "active",
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_club_rejoin@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    joined = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_headers)
    assert joined.status_code == 200
    first_membership_id = joined.json()["membership_id"]

    removed = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/members/{first_membership_id}",
        json={"status": "removed"},
        headers=admin_headers,
    )
    assert removed.status_code == 200
    assert removed.json()["status"] == "removed"

    rejoined = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_headers)
    assert rejoined.status_code == 200
    assert rejoined.json()["membership_id"] == first_membership_id

    members = client.get(f"/api/v1/clubs/{club.json()['id']}/members", headers=admin_headers)
    assert members.status_code == 200
    assert len(members.json()) == 1
    assert members.json()[0]["status"] == "active"


def test_student_can_reregister_after_rejection_without_duplicate_record() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_event_reregister@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_event_reregister@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Retry",
            "email": "student_event_reregister@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_event_reregister@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Media Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_event_reregister@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Podcast Bootcamp",
            "capacity": 20,
            "approval_required": True,
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_event_reregister@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    first_attempt = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert first_attempt.status_code == 201
    registration_id = first_attempt.json()["id"]

    rejected = client.patch(
        f"/api/v1/event-registrations/{registration_id}",
        json={"status": "rejected"},
        headers=coordinator_headers,
    )
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"

    second_attempt = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert second_attempt.status_code == 201
    assert second_attempt.json()["id"] == registration_id
    assert second_attempt.json()["status"] == "pending"

    registrations = client.get(
        f"/api/v1/event-registrations/?event_id={event.json()['id']}",
        headers=coordinator_headers,
    )
    assert registrations.status_code == 200
    assert len(registrations.json()) == 1
    assert registrations.json()[0]["status"] == "pending"


def test_draft_club_is_not_marked_active_in_response() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_draft_flag@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_draft_flag@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Draft Club",
            "description": "Club",
            "status": "draft",
        },
        headers=admin_headers,
    )
    assert club.status_code == 201
    assert club.json()["is_active"] is False


def test_club_analytics_uses_confirmed_event_fill_rate() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_fill_rate@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_fill_rate@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_club_fill_rate@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_club_fill_rate@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_fill_rate@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Innovation Forum",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_fill_rate@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Prototype Day",
            "capacity": 10,
            "approval_required": True,
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_club_fill_rate@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    reg_one = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_one_headers,
    )
    assert reg_one.status_code == 201

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_club_fill_rate@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    reg_two = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_two_headers,
    )
    assert reg_two.status_code == 201

    approved = client.patch(
        f"/api/v1/event-registrations/{reg_one.json()['id']}",
        json={"status": "approved"},
        headers=coordinator_headers,
    )
    assert approved.status_code == 200

    analytics = client.get(
        f"/api/v1/clubs/{club.json()['id']}/analytics",
        headers=coordinator_headers,
    )
    assert analytics.status_code == 200
    assert analytics.json()["average_attendance_pct"] == 10.0


def test_full_event_adds_student_to_waitlist_instead_of_rejecting() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_event_waitlist@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_event_waitlist@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_event_waitlist@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_event_waitlist@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_event_waitlist@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Waitlist Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "status": "active",
            "registration_open": True,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_event_waitlist@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Limited Workshop",
            "capacity": 1,
            "status": "open",
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_event_waitlist@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    first_registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_one_headers,
    )
    assert first_registration.status_code == 201
    assert first_registration.json()["status"] == "registered"

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_event_waitlist@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    second_registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_two_headers,
    )
    assert second_registration.status_code == 201
    assert second_registration.json()["status"] == "waitlisted"

    registrations = client.get(
        f"/api/v1/event-registrations/?event_id={event.json()['id']}",
        headers=coordinator_headers,
    )
    assert registrations.status_code == 200
    statuses = {row["student_email"] or row["email"]: row["status"] for row in registrations.json()}
    assert statuses["student_one_event_waitlist@example.com"] == "registered"
    assert statuses["student_two_event_waitlist@example.com"] == "waitlisted"

    visible_event = client.get(
        f"/api/v1/club-events/?club_id={club.json()['id']}",
        headers=student_two_headers,
    )
    assert visible_event.status_code == 200
    assert visible_event.json()[0]["status"] == "open"


def test_cancelling_confirmed_registration_promotes_oldest_waitlisted_student() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_event_waitlist_promote@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_event_waitlist_promote@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_event_waitlist_promote@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_event_waitlist_promote@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_event_waitlist_promote@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Promotion Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "status": "active",
            "registration_open": True,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_event_waitlist_promote@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Promotion Workshop",
            "capacity": 1,
            "status": "open",
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_event_waitlist_promote@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    first_registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_one_headers,
    )
    assert first_registration.status_code == 201
    assert first_registration.json()["status"] == "registered"

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_event_waitlist_promote@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    second_registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_two_headers,
    )
    assert second_registration.status_code == 201
    assert second_registration.json()["status"] == "waitlisted"

    cancelled = client.patch(
        f"/api/v1/event-registrations/{first_registration.json()['id']}",
        json={"status": "cancelled"},
        headers=coordinator_headers,
    )
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"

    registrations = client.get(
        f"/api/v1/event-registrations/?event_id={event.json()['id']}",
        headers=coordinator_headers,
    )
    assert registrations.status_code == 200
    statuses = {row["student_email"] or row["email"]: row["status"] for row in registrations.json()}
    assert statuses["student_one_event_waitlist_promote@example.com"] == "cancelled"
    assert statuses["student_two_event_waitlist_promote@example.com"] == "registered"


def test_club_analytics_include_event_waitlist_and_review_pressure() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_waitlist_analytics@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_waitlist_analytics@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_club_waitlist_analytics@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_club_waitlist_analytics@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_three = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Three",
            "email": "student_three_club_waitlist_analytics@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201
    assert student_three.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_waitlist_analytics@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Queue Signals Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "status": "active",
            "registration_open": True,
            "membership_type": "approval_required",
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_waitlist_analytics@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    full_event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Full House Event",
            "capacity": 1,
            "status": "open",
        },
        headers=coordinator_headers,
    )
    review_event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Approval Event",
            "capacity": 5,
            "approval_required": True,
            "status": "open",
        },
        headers=coordinator_headers,
    )
    assert full_event.status_code == 201
    assert review_event.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_club_waitlist_analytics@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    confirmed = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": full_event.json()["id"]},
        headers=student_one_headers,
    )
    assert confirmed.status_code == 201
    assert confirmed.json()["status"] == "registered"

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_club_waitlist_analytics@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    waitlisted = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": full_event.json()["id"]},
        headers=student_two_headers,
    )
    assert waitlisted.status_code == 201
    assert waitlisted.json()["status"] == "waitlisted"

    student_three_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_three_club_waitlist_analytics@example.com", "password": "password123"},
    )
    student_three_headers = {"Authorization": f"Bearer {student_three_login.json()['access_token']}"}
    pending = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": review_event.json()["id"]},
        headers=student_three_headers,
    )
    assert pending.status_code == 201
    assert pending.json()["status"] == "pending"

    application = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_three_headers)
    assert application.status_code == 200
    assert application.json()["status"] == "pending"

    analytics = client.get(
        f"/api/v1/clubs/{club.json()['id']}/analytics",
        headers=coordinator_headers,
    )
    assert analytics.status_code == 200
    payload = analytics.json()
    assert payload["confirmed_event_registrations"] == 1
    assert payload["pending_event_registrations"] == 1
    assert payload["waitlisted_event_registrations"] == 1
    assert payload["events_at_capacity"] == 1
    assert payload["pending_applications"] == 1


def test_club_analytics_include_attendance_and_certificate_quality() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_delivery_analytics@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_delivery_analytics@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_club_delivery_analytics@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_club_delivery_analytics@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_delivery_analytics@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Delivery Metrics Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_delivery_analytics@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Certified Workshop",
            "capacity": 10,
            "status": "completed",
            "certificate_enabled": True,
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_club_delivery_analytics@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    reg_one = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_one_headers,
    )
    assert reg_one.status_code == 201

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_club_delivery_analytics@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    reg_two = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_two_headers,
    )
    assert reg_two.status_code == 201

    mark_one = client.patch(
        f"/api/v1/event-registrations/{reg_one.json()['id']}",
        json={"attendance_status": "present"},
        headers=coordinator_headers,
    )
    assert mark_one.status_code == 200
    issue_certificate = client.patch(
        f"/api/v1/event-registrations/{reg_one.json()['id']}",
        json={"certificate_issued": True},
        headers=coordinator_headers,
    )
    assert issue_certificate.status_code == 200
    mark_two = client.patch(
        f"/api/v1/event-registrations/{reg_two.json()['id']}",
        json={"attendance_status": "absent"},
        headers=coordinator_headers,
    )
    assert mark_two.status_code == 200

    analytics = client.get(
        f"/api/v1/clubs/{club.json()['id']}/analytics",
        headers=coordinator_headers,
    )
    assert analytics.status_code == 200
    payload = analytics.json()
    assert payload["attendance_marked_registrations"] == 2
    assert payload["attendance_marked_pct"] == 100.0
    assert payload["present_attendance_count"] == 1
    assert payload["absent_attendance_count"] == 1
    assert payload["no_show_rate_pct"] == 50.0
    assert payload["certificate_enabled_events"] == 1
    assert payload["certificate_eligible_registrations"] == 1
    assert payload["certificates_issued"] == 1
    assert payload["certificate_issuance_pct"] == 100.0
    assert payload["event_performance"][0]["title"] == "Certified Workshop"
    assert payload["event_performance"][0]["attendance_marked_pct"] == 100.0
    assert payload["event_performance"][0]["certificate_issuance_pct"] == 100.0


def test_club_analytics_prioritize_waitlist_pressure_in_event_performance() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_event_health_order@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_event_health_order@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    students = []
    for index in range(3):
        response = client.post(
            "/api/v1/auth/register",
            json={
                "full_name": f"Student {index}",
                "email": f"student_{index}_club_event_health_order@example.com",
                "password": "password123",
                "role": "student",
            },
        )
        students.append(response)
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert all(item.status_code == 201 for item in students)

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_event_health_order@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Event Health Order Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_event_health_order@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    queue_event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Overflow Event",
            "capacity": 1,
            "status": "open",
        },
        headers=coordinator_headers,
    )
    quiet_event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Quiet Event",
            "capacity": 10,
            "status": "open",
        },
        headers=coordinator_headers,
    )
    assert queue_event.status_code == 201
    assert quiet_event.status_code == 201

    for index, student in enumerate(students):
        login = client.post(
            "/api/v1/auth/login",
            json={"email": f"student_{index}_club_event_health_order@example.com", "password": "password123"},
        )
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
        target_event_id = queue_event.json()["id"] if index < 2 else quiet_event.json()["id"]
        created = client.post("/api/v1/event-registrations/", json={"event_id": target_event_id}, headers=headers)
        assert created.status_code == 201

    analytics = client.get(
        f"/api/v1/clubs/{club.json()['id']}/analytics",
        headers=coordinator_headers,
    )
    assert analytics.status_code == 200
    payload = analytics.json()
    assert payload["waitlist_pressure_events"] == 1
    assert payload["event_performance"][0]["title"] == "Overflow Event"
    assert payload["event_performance"][0]["health_summary"] == "waitlist pressure"


def test_club_event_performance_export_returns_csv() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_export_perf@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_export_perf@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student",
            "email": "student_club_export_perf@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_export_perf@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Performance Export Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_export_perf@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Performance Export Event",
            "capacity": 1,
            "status": "open",
            "certificate_enabled": True,
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_club_export_perf@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert registration.status_code == 201

    export_response = client.get(
        f"/api/v1/clubs/{club.json()['id']}/analytics/export",
        params={"report": "event_performance"},
        headers=coordinator_headers,
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "event-performance-report" in export_response.headers["content-disposition"]
    rows = list(csv.DictReader(StringIO(export_response.text)))
    assert len(rows) == 1
    assert rows[0]["event_title"] == "Performance Export Event"
    assert rows[0]["confirmed_registrations"] == "1"
    assert rows[0]["certificate_enabled"] == "yes"


def test_club_attendance_certificate_export_returns_csv() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_export_attendance@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_export_attendance@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Export",
            "email": "student_club_export_attendance@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_export_attendance@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Attendance Export Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_export_attendance@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Attendance Export Event",
            "capacity": 5,
            "status": "completed",
            "certificate_enabled": True,
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_club_export_attendance@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert registration.status_code == 201

    mark_present = client.patch(
        f"/api/v1/event-registrations/{registration.json()['id']}",
        json={"attendance_status": "present"},
        headers=coordinator_headers,
    )
    assert mark_present.status_code == 200
    issue_certificate = client.patch(
        f"/api/v1/event-registrations/{registration.json()['id']}",
        json={"certificate_issued": True},
        headers=coordinator_headers,
    )
    assert issue_certificate.status_code == 200

    export_response = client.get(
        f"/api/v1/clubs/{club.json()['id']}/analytics/export",
        params={"report": "attendance_certificate"},
        headers=coordinator_headers,
    )
    assert export_response.status_code == 200
    assert export_response.headers["content-type"].startswith("text/csv")
    assert "attendance-certificate-report" in export_response.headers["content-disposition"]
    rows = list(csv.DictReader(StringIO(export_response.text)))
    assert len(rows) == 1
    assert rows[0]["event_title"] == "Attendance Export Event"
    assert rows[0]["student_name"] == "Student Export"
    assert rows[0]["attendance_status"] == "present"
    assert rows[0]["certificate_eligible"] == "yes"
    assert rows[0]["certificate_issued"] == "yes"


def test_club_application_context_update_persists_owner_note_and_touch_metadata() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_club_context@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator Context", "email": "coord_club_context@example.com", "password": "password123", "role": "teacher"},
    )
    student = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Student Applicant", "email": "student_club_context@example.com", "password": "password123", "role": "student"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_club_context@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Club Context",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "approval_required",
            "status": "active",
            "registration_open": True,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    student_login = client.post("/api/v1/auth/login", json={"email": "student_club_context@example.com", "password": "password123"})
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    join_response = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_headers)
    assert join_response.status_code == 200
    assert join_response.json()["status"] == "pending"

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_club_context@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    applications = client.get(f"/api/v1/clubs/{club.json()['id']}/applications", headers=coordinator_headers)
    assert applications.status_code == 200
    application = applications.json()[0]

    context_update = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/applications/{application['id']}",
        json={
            "queue_owner_user_id": coordinator.json()["id"],
            "coordinator_note": "Call student before Friday review.",
        },
        headers=coordinator_headers,
    )
    assert context_update.status_code == 200
    payload = context_update.json()
    assert payload["queue_owner_user_id"] == coordinator.json()["id"]
    assert "Coordinator Context" in (payload["queue_owner_label"] or "")
    assert payload["coordinator_note"] == "Call student before Friday review."
    assert payload["last_touched_by"] == coordinator.json()["id"]
    assert "Coordinator Context" in (payload["last_touched_by_label"] or "")
    assert payload["last_touched_at"] is not None
    assert payload["status"] == "pending"


def test_event_registration_context_update_persists_owner_note_and_touch_metadata() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_event_context@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator Event", "email": "coord_event_context@example.com", "password": "password123", "role": "teacher"},
    )
    student = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Student Event", "email": "student_event_context@example.com", "password": "password123", "role": "student"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_event_context@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Event Context Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_event_context@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Context Event", "capacity": 10, "status": "open"},
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post("/api/v1/auth/login", json={"email": "student_event_context@example.com", "password": "password123"})
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert registration.status_code == 201

    context_update = client.patch(
        f"/api/v1/event-registrations/{registration.json()['id']}",
        json={
            "queue_owner_user_id": coordinator.json()["id"],
            "coordinator_note": "Needs attendance follow-up after event.",
        },
        headers=coordinator_headers,
    )
    assert context_update.status_code == 200
    payload = context_update.json()
    assert payload["queue_owner_user_id"] == coordinator.json()["id"]
    assert "Coordinator Event" in (payload["queue_owner_label"] or "")
    assert payload["coordinator_note"] == "Needs attendance follow-up after event."
    assert payload["last_touched_by"] == coordinator.json()["id"]
    assert "Coordinator Event" in (payload["last_touched_by_label"] or "")
    assert payload["last_touched_at"] is not None
    assert payload["status"] == "registered"


def test_club_event_history_drilldown_includes_lifecycle_timeline() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_event_history@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator History", "email": "coord_event_history@example.com", "password": "password123", "role": "teacher"},
    )
    student = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Student History", "email": "student_event_history@example.com", "password": "password123", "role": "student"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_event_history@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Event History Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_event_history@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Timeline Event",
            "capacity": 5,
            "status": "open",
            "certificate_enabled": True,
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post("/api/v1/auth/login", json={"email": "student_event_history@example.com", "password": "password123"})
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post("/api/v1/event-registrations/", json={"event_id": event.json()["id"]}, headers=student_headers)
    assert registration.status_code == 201

    close_event = client.put(
        f"/api/v1/club-events/{event.json()['id']}",
        json={"status": "completed", "result_summary": "Timeline captured."},
        headers=coordinator_headers,
    )
    assert close_event.status_code == 200

    mark_present = client.patch(
        f"/api/v1/event-registrations/{registration.json()['id']}",
        json={"attendance_status": "present"},
        headers=coordinator_headers,
    )
    assert mark_present.status_code == 200

    issue_certificate = client.patch(
        f"/api/v1/event-registrations/{registration.json()['id']}",
        json={"certificate_issued": True},
        headers=coordinator_headers,
    )
    assert issue_certificate.status_code == 200

    history = client.get(
        f"/api/v1/clubs/{club.json()['id']}/events/{event.json()['id']}/history",
        headers=coordinator_headers,
    )
    assert history.status_code == 200
    payload = history.json()
    assert payload["title"] == "Timeline Event"
    assert payload["status"] == "completed"
    assert payload["confirmed_registrations"] == 1
    assert payload["attendance_marked_count"] == 1
    assert payload["certificates_issued"] == 1
    titles = [item["title"] for item in payload["timeline"]]
    assert "Event updated" in titles
    assert "Registration created" in titles
    assert "Attendance updated" in titles
    assert "Certificate status updated" in titles
    assert any(item["entry_type"] == "queue_snapshot" for item in payload["timeline"])


def test_club_analytics_include_cross_event_trends() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_club_trends@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator Trends", "email": "coord_club_trends@example.com", "password": "password123", "role": "teacher"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_club_trends@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Trend Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    club_id = club.json()["id"]
    base_date = datetime(2026, 1, 10, tzinfo=timezone.utc)
    event_specs = [
        {"title": "Trend Event 1", "fill": 20.0, "no_show": 60.0, "cert": 0.0, "waitlisted": 0, "health": "attendance risk"},
        {"title": "Trend Event 2", "fill": 40.0, "no_show": 50.0, "cert": 25.0, "waitlisted": 0, "health": "certificate follow-up"},
        {"title": "Trend Event 3", "fill": 80.0, "no_show": 20.0, "cert": 75.0, "waitlisted": 1, "health": "waitlist pressure"},
        {"title": "Trend Event 4", "fill": 100.0, "no_show": 10.0, "cert": 100.0, "waitlisted": 2, "health": "waitlist pressure"},
    ]
    for index, spec in enumerate(event_specs):
        event_id = ObjectId()
        fake_db.club_events.items.append(
            {
                "_id": event_id,
                "club_id": club_id,
                "title": spec["title"],
                "status": "completed",
                "event_type": "workshop",
                "event_date": base_date.replace(day=10 + index),
                "capacity": 10,
                "certificate_enabled": True,
            }
        )
        confirmed = int(spec["fill"] // 10)
        present = max(0, round(confirmed * (1 - (spec["no_show"] / 100))))
        absent = max(0, confirmed - present)
        issued = min(present, round(present * (spec["cert"] / 100)))
        for reg_index in range(confirmed):
            fake_db.event_registrations.items.append(
                {
                    "_id": ObjectId(),
                    "event_id": str(event_id),
                    "student_user_id": str(ObjectId()),
                    "status": "registered",
                    "attendance_status": "present" if reg_index < present else "absent",
                    "certificate_issued": reg_index < issued,
                }
            )
        for _ in range(spec["waitlisted"]):
            fake_db.event_registrations.items.append(
                {
                    "_id": ObjectId(),
                    "event_id": str(event_id),
                    "student_user_id": str(ObjectId()),
                    "status": "waitlisted",
                }
            )

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_club_trends@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    analytics = client.get(f"/api/v1/clubs/{club_id}/analytics", headers=coordinator_headers)
    assert analytics.status_code == 200
    payload = analytics.json()
    trend_map = {item["key"]: item for item in payload["trend_summaries"]}
    assert trend_map["demand"]["direction"] == "improving"
    assert trend_map["attendance"]["direction"] == "improving"
    assert trend_map["certificate"]["direction"] == "improving"
    assert payload["repeat_attention_events"] == 4
    assert len(payload["recent_event_trends"]) == 4
    assert payload["recent_event_trends"][-1]["title"] == "Trend Event 4"


def test_club_analytics_include_archival_rollups() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_club_archive_analytics@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator Archive", "email": "coord_club_archive_analytics@example.com", "password": "password123", "role": "teacher"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_club_archive_analytics@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Archive Analytics Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    club_id = club.json()["id"]
    now = datetime.now(timezone.utc)
    archived_specs = [
        {"title": "Archive Recent", "event_date": now - timedelta(days=30), "confirmed": 3, "present": 2, "absent": 1, "issued": 2},
        {"title": "Archive Mid", "event_date": now - timedelta(days=180), "confirmed": 4, "present": 3, "absent": 1, "issued": 2},
        {"title": "Archive Legacy", "event_date": now - timedelta(days=500), "confirmed": 2, "present": 2, "absent": 0, "issued": 1},
    ]
    for spec in archived_specs:
        event_id = ObjectId()
        fake_db.club_events.items.append(
            {
                "_id": event_id,
                "club_id": club_id,
                "title": spec["title"],
                "status": "archived",
                "event_type": "workshop",
                "event_date": spec["event_date"],
                "created_at": spec["event_date"],
                "capacity": max(spec["confirmed"], 1),
                "certificate_enabled": True,
            }
        )
        for reg_index in range(spec["confirmed"]):
            attendance_status = "present" if reg_index < spec["present"] else "absent"
            fake_db.event_registrations.items.append(
                {
                    "_id": ObjectId(),
                    "event_id": str(event_id),
                    "student_user_id": str(ObjectId()),
                    "status": "registered",
                    "attendance_status": attendance_status,
                    "certificate_issued": attendance_status == "present" and reg_index < spec["issued"],
                }
            )

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_club_archive_analytics@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    analytics = client.get(f"/api/v1/clubs/{club_id}/analytics", headers=coordinator_headers)
    assert analytics.status_code == 200
    payload = analytics.json()

    assert payload["archived_events"] == 3
    assert payload["archived_confirmed_registrations"] == 9
    assert payload["archived_attendance_marked_pct"] == 100.0
    assert payload["archived_no_show_rate_pct"] == round((2 / 9) * 100, 2)
    assert payload["archived_certificates_issued"] == 5
    assert payload["archived_certificate_issuance_pct"] == round((5 / 7) * 100, 2)

    season_labels = [item["season_label"] for item in payload["archive_season_summaries"]]
    expected_labels = {
        f"{(now - timedelta(days=30)).year} Q{(((now - timedelta(days=30)).month - 1) // 3) + 1}",
        f"{(now - timedelta(days=180)).year} Q{(((now - timedelta(days=180)).month - 1) // 3) + 1}",
        f"{(now - timedelta(days=500)).year} Q{(((now - timedelta(days=500)).month - 1) // 3) + 1}",
    }
    assert expected_labels.issubset(set(season_labels))

    cohort_map = {item["cohort_key"]: item for item in payload["archive_event_cohorts"]}
    assert cohort_map["last_90_days"]["archived_events"] == 1
    assert cohort_map["91_to_365_days"]["archived_events"] == 1
    assert cohort_map["older_than_365_days"]["archived_events"] == 1
    assert len(payload["archival_history_points"]) >= 3


def test_club_analytics_include_financial_and_sponsorship_insight() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_club_finance@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator Finance", "email": "coord_club_finance@example.com", "password": "password123", "role": "teacher"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_club_finance@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Finance Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201
    club_id = club.json()["id"]

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_club_finance@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    sponsorship_update = client.patch(
        f"/api/v1/clubs/{club_id}",
        json={
            "sponsorship_target_amount": 50000,
            "sponsorship_committed_amount": 12000,
            "sponsorship_notes": "Two local partners confirmed."
        },
        headers=coordinator_headers,
    )
    assert sponsorship_update.status_code == 200
    assert sponsorship_update.json()["sponsorship_target_amount"] == 50000
    assert sponsorship_update.json()["sponsorship_committed_amount"] == 12000

    paid_event_id = ObjectId()
    free_event_id = ObjectId()
    fake_db.club_events.items.extend(
        [
            {
                "_id": paid_event_id,
                "club_id": club_id,
                "title": "Paid Bootcamp",
                "status": "completed",
                "event_type": "workshop",
                "event_date": datetime(2026, 4, 1, tzinfo=timezone.utc),
                "capacity": 50,
                "certificate_enabled": True,
                "payment_required": True,
                "payment_amount": 500,
            },
            {
                "_id": free_event_id,
                "club_id": club_id,
                "title": "Free Meetup",
                "status": "completed",
                "event_type": "meetup",
                "event_date": datetime(2026, 4, 2, tzinfo=timezone.utc),
                "capacity": 40,
                "certificate_enabled": False,
                "payment_required": False,
                "payment_amount": None,
            },
        ]
    )
    fake_db.event_registrations.items.extend(
        [
            {
                "_id": ObjectId(),
                "event_id": str(paid_event_id),
                "student_user_id": str(ObjectId()),
                "status": "registered",
                "attendance_status": "present",
                "certificate_issued": True,
                "payment_qr_code": "TXN-1001",
            },
            {
                "_id": ObjectId(),
                "event_id": str(paid_event_id),
                "student_user_id": str(ObjectId()),
                "status": "approved",
                "attendance_status": "present",
                "certificate_issued": False,
            },
            {
                "_id": ObjectId(),
                "event_id": str(free_event_id),
                "student_user_id": str(ObjectId()),
                "status": "registered",
                "attendance_status": "present",
                "certificate_issued": False,
            },
        ]
    )

    analytics = client.get(f"/api/v1/clubs/{club_id}/analytics", headers=coordinator_headers)
    assert analytics.status_code == 200
    payload = analytics.json()

    assert payload["paid_events_count"] == 1
    assert payload["free_events_count"] == 1
    assert payload["paid_confirmed_registrations"] == 2
    assert payload["payment_proof_submitted_count"] == 1
    assert payload["payment_proof_coverage_pct"] == 50.0
    assert payload["listed_paid_revenue_inr"] == 1000.0
    assert payload["sponsorship_target_amount"] == 50000.0
    assert payload["sponsorship_committed_amount"] == 12000.0
    assert payload["sponsorship_gap_amount"] == 38000.0
    assert payload["sponsorship_progress_pct"] == 24.0


def test_club_analytics_include_engagement_intelligence() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_club_engagement@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator Engagement", "email": "coord_club_engagement@example.com", "password": "password123", "role": "teacher"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_club_engagement@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Engagement Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201
    club_id = club.json()["id"]

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_club_engagement@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}

    now = datetime.now(timezone.utc)
    member_one = str(ObjectId())
    member_two = str(ObjectId())
    member_three = str(ObjectId())
    member_four = str(ObjectId())
    member_five = str(ObjectId())
    fake_db.club_members.items.extend(
        [
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "student_user_id": member_one,
                "status": "active",
                "joined_at": now - timedelta(days=200),
            },
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "student_user_id": member_two,
                "status": "active",
                "joined_at": now - timedelta(days=180),
            },
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "student_user_id": member_three,
                "status": "active",
                "joined_at": now - timedelta(days=20),
            },
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "student_user_id": member_four,
                "status": "inactive",
                "joined_at": now - timedelta(days=160),
                "left_at": now - timedelta(days=10),
            },
            {
                "_id": ObjectId(),
                "club_id": club_id,
                "student_user_id": member_five,
                "status": "removed",
                "joined_at": now - timedelta(days=220),
                "left_at": now - timedelta(days=140),
            },
        ]
    )

    recent_event_id = ObjectId()
    legacy_event_id = ObjectId()
    fake_db.club_events.items.extend(
        [
            {
                "_id": recent_event_id,
                "club_id": club_id,
                "title": "Recent Showcase",
                "status": "completed",
                "event_type": "showcase",
                "event_date": now - timedelta(days=20),
                "capacity": 30,
                "certificate_enabled": False,
                "payment_required": False,
            },
            {
                "_id": legacy_event_id,
                "club_id": club_id,
                "title": "Legacy Meetup",
                "status": "completed",
                "event_type": "meetup",
                "event_date": now - timedelta(days=140),
                "capacity": 20,
                "certificate_enabled": False,
                "payment_required": False,
            },
        ]
    )
    fake_db.event_registrations.items.extend(
        [
            {
                "_id": ObjectId(),
                "event_id": str(recent_event_id),
                "student_user_id": member_one,
                "status": "registered",
                "attendance_status": "present",
                "certificate_issued": False,
            },
            {
                "_id": ObjectId(),
                "event_id": str(legacy_event_id),
                "student_user_id": member_four,
                "status": "registered",
                "attendance_status": "absent",
                "certificate_issued": False,
            },
            {
                "_id": ObjectId(),
                "event_id": str(legacy_event_id),
                "student_user_id": member_five,
                "status": "registered",
                "attendance_status": "present",
                "certificate_issued": False,
            },
        ]
    )

    analytics = client.get(f"/api/v1/clubs/{club_id}/analytics", headers=coordinator_headers)
    assert analytics.status_code == 200
    payload = analytics.json()

    assert payload["retained_members_90d"] == 2
    assert payload["departed_members_90d"] == 1
    assert payload["member_retention_pct_90d"] == 66.67
    assert payload["member_churn_rate_pct_90d"] == 33.33
    assert payload["members_with_event_participation"] == 3
    assert payload["members_with_present_attendance"] == 2
    assert payload["member_event_conversion_pct"] == 60.0
    assert payload["member_attendance_conversion_pct"] == 40.0
    assert payload["recently_engaged_active_members_90d"] == 1
    assert payload["at_risk_active_members_90d"] == 1


def test_club_analytics_include_membership_waitlist_pressure() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_membership_waitlist_analytics@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_membership_waitlist_analytics@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_membership_waitlist_analytics@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_membership_waitlist_analytics@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_membership_waitlist_analytics@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Membership Waitlist Metrics Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "open",
            "registration_open": True,
            "status": "active",
            "max_members": 1,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_membership_waitlist_analytics@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    joined = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_one_headers)
    assert joined.status_code == 200
    assert joined.json()["status"] == "approved"

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_membership_waitlist_analytics@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    waitlisted = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_two_headers)
    assert waitlisted.status_code == 200
    assert waitlisted.json()["status"] == "waitlisted"

    analytics = client.get(
        f"/api/v1/clubs/{club.json()['id']}/analytics",
        headers=admin_headers,
    )
    assert analytics.status_code == 200
    payload = analytics.json()
    assert payload["pending_applications"] == 0
    assert payload["waitlisted_applications"] == 1


def test_club_application_bulk_review_updates_selected_queue_items() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_bulk_club_review@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_bulk_club_review@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_bulk_club_review@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_bulk_club_review@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_bulk_club_review@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Bulk Review Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "approval_required",
            "registration_open": True,
            "status": "active",
            "max_members": 5,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_bulk_club_review@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    application_one = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_one_headers)
    assert application_one.status_code == 200

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_bulk_club_review@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    application_two = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_two_headers)
    assert application_two.status_code == 200

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_bulk_club_review@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    reviewed = client.post(
        f"/api/v1/clubs/{club.json()['id']}/applications/bulk-review",
        json={
            "application_ids": [
                application_one.json()["application_id"],
                application_two.json()["application_id"],
            ],
            "status": "approved",
        },
        headers=coordinator_headers,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["updated_count"] == 2

    applications = client.get(
        f"/api/v1/clubs/{club.json()['id']}/applications",
        headers=coordinator_headers,
    )
    assert applications.status_code == 200
    assert [item["status"] for item in applications.json()] == ["approved", "approved"]
    assert len([
        item for item in fake_db.club_members.items
        if item["club_id"] == club.json()["id"] and item["status"] == "active"
    ]) == 2


def test_club_application_reminder_creates_notifications_for_waitlist() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_queue_reminder@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_queue_reminder@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Waitlist",
            "email": "student_club_queue_reminder@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    member = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Existing Member",
            "email": "existing_member_club_queue_reminder@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201
    assert member.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_queue_reminder@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Reminder Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "open",
            "registration_open": True,
            "status": "active",
            "max_members": 1,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    member_login = client.post(
        "/api/v1/auth/login",
        json={"email": "existing_member_club_queue_reminder@example.com", "password": "password123"},
    )
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}
    joined = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=member_headers)
    assert joined.status_code == 200

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_club_queue_reminder@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    waitlisted = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_headers)
    assert waitlisted.status_code == 200
    assert waitlisted.json()["status"] == "waitlisted"

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_queue_reminder@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    reminded = client.post(
        f"/api/v1/clubs/{club.json()['id']}/applications/remind",
        json={"status_filter": "waitlisted", "message": "Seat updates are on the way."},
        headers=coordinator_headers,
    )
    assert reminded.status_code == 200
    assert reminded.json()["reminded_count"] == 1
    assert len(fake_db.notifications.items) == 1
    assert fake_db.notifications.items[0]["target_user_id"] == student.json()["id"]
    assert fake_db.notifications.items[0]["message"] == "Seat updates are on the way."


def test_club_application_shared_views_are_visible_across_managers() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_club_shared_view@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator", "email": "coord_club_shared_view@example.com", "password": "password123", "role": "teacher"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_club_shared_view@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Shared Club Queue View",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "approval_required",
            "registration_open": True,
            "status": "active",
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_club_shared_view@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    created = client.post(
        f"/api/v1/clubs/{club.json()['id']}/applications/views",
        json={
            "name": "Waitlist First",
            "filters": {"search": "wait", "status": "waitlisted", "page_size": 12},
        },
        headers=coordinator_headers,
    )
    assert created.status_code == 201

    listed = client.get(f"/api/v1/clubs/{club.json()['id']}/applications/views", headers=admin_headers)
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Waitlist First"
    assert listed.json()[0]["filters"]["status"] == "waitlisted"
    assert listed.json()[0]["created_by_label"] == "Coordinator"


def test_club_application_history_persists_waitlist_snapshots() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_club_history@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator", "email": "coord_club_history@example.com", "password": "password123", "role": "teacher"},
    )
    member = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Member", "email": "member_club_history@example.com", "password": "password123", "role": "student"},
    )
    student = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Waitlist Student", "email": "student_club_history@example.com", "password": "password123", "role": "student"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert member.status_code == 201
    assert student.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_club_history@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Club Queue History",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "membership_type": "open",
            "registration_open": True,
            "status": "active",
            "max_members": 1,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    member_login = client.post("/api/v1/auth/login", json={"email": "member_club_history@example.com", "password": "password123"})
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}
    assert client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=member_headers).status_code == 200

    student_login = client.post("/api/v1/auth/login", json={"email": "student_club_history@example.com", "password": "password123"})
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    waitlisted = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_headers)
    assert waitlisted.status_code == 200
    assert waitlisted.json()["status"] == "waitlisted"

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_club_history@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    history = client.get(f"/api/v1/clubs/{club.json()['id']}/applications/history", headers=coordinator_headers)
    assert history.status_code == 200
    assert history.json()[0]["total"] == 1
    assert history.json()[0]["waitlisted"] == 1
    assert history.json()[0]["source_action"] == "join_waitlist"


def test_event_registration_bulk_update_reviews_selected_queue_items() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_bulk_event_review@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_bulk_event_review@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student One",
            "email": "student_one_bulk_event_review@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Two",
            "email": "student_two_bulk_event_review@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_bulk_event_review@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Bulk Event Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_bulk_event_review@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Bulk Review Event",
            "capacity": 5,
            "approval_required": True,
            "status": "open",
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_one_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_one_bulk_event_review@example.com", "password": "password123"},
    )
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    registration_one = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_one_headers,
    )
    assert registration_one.status_code == 201
    assert registration_one.json()["status"] == "pending"

    student_two_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_two_bulk_event_review@example.com", "password": "password123"},
    )
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    registration_two = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_two_headers,
    )
    assert registration_two.status_code == 201
    assert registration_two.json()["status"] == "pending"

    reviewed = client.post(
        "/api/v1/event-registrations/bulk-update",
        json={
            "registration_ids": [registration_one.json()["id"], registration_two.json()["id"]],
            "status": "approved",
        },
        headers=coordinator_headers,
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["updated_count"] == 2

    listed = client.get(
        f"/api/v1/event-registrations/?event_id={event.json()['id']}",
        headers=coordinator_headers,
    )
    assert listed.status_code == 200
    assert [item["status"] for item in listed.json()] == ["approved", "approved"]


def test_event_registration_reminder_creates_notifications_for_selected_queue() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_event_queue_reminder@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_event_queue_reminder@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Queue",
            "email": "student_event_queue_reminder@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_event_queue_reminder@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Reminder Event Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_event_queue_reminder@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Reminder Event",
            "capacity": 2,
            "approval_required": True,
            "status": "open",
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_event_queue_reminder@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert registration.status_code == 201
    assert registration.json()["status"] == "pending"

    reminded = client.post(
        "/api/v1/event-registrations/remind",
        json={
            "event_id": event.json()["id"],
            "registration_ids": [registration.json()["id"]],
            "message": "Please keep an eye on your queue status.",
        },
        headers=coordinator_headers,
    )
    assert reminded.status_code == 200
    assert reminded.json()["reminded_count"] == 1
    assert len(fake_db.notifications.items) == 1
    assert fake_db.notifications.items[0]["target_user_id"] == student.json()["id"]
    assert fake_db.notifications.items[0]["message"] == "Please keep an eye on your queue status."


def test_event_registration_shared_views_are_visible_across_managers() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_event_shared_view@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator", "email": "coord_event_shared_view@example.com", "password": "password123", "role": "teacher"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_event_shared_view@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Event Queue Shared View Club", "description": "Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_event_shared_view@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Event Queue Shared View", "approval_required": True, "status": "open"},
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    created = client.post(
        f"/api/v1/event-registrations/views?event_id={event.json()['id']}",
        json={"name": "Pending First", "filters": {"search": "pending", "status": "pending", "page_size": 20}},
        headers=coordinator_headers,
    )
    assert created.status_code == 201

    listed = client.get(
        f"/api/v1/event-registrations/views?event_id={event.json()['id']}",
        headers=admin_headers,
    )
    assert listed.status_code == 200
    assert listed.json()[0]["name"] == "Pending First"
    assert listed.json()[0]["filters"]["status"] == "pending"
    assert listed.json()[0]["created_by_label"] == "Coordinator"


def test_event_registration_history_persists_waitlist_snapshots() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Admin", "email": "admin_event_history@example.com", "password": "password123", "role": "admin"},
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Coordinator", "email": "coord_event_history@example.com", "password": "password123", "role": "teacher"},
    )
    student_one = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Student One", "email": "student_one_event_history@example.com", "password": "password123", "role": "student"},
    )
    student_two = client.post(
        "/api/v1/auth/register",
        json={"full_name": "Student Two", "email": "student_two_event_history@example.com", "password": "password123", "role": "student"},
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student_one.status_code == 201
    assert student_two.status_code == 201

    admin_login = client.post("/api/v1/auth/login", json={"email": "admin_event_history@example.com", "password": "password123"})
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={"name": "Event Queue History Club", "description": "Club", "coordinator_user_id": coordinator.json()["id"]},
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post("/api/v1/auth/login", json={"email": "coord_event_history@example.com", "password": "password123"})
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={"club_id": club.json()["id"], "title": "Event Queue History", "capacity": 1, "status": "open"},
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_one_login = client.post("/api/v1/auth/login", json={"email": "student_one_event_history@example.com", "password": "password123"})
    student_one_headers = {"Authorization": f"Bearer {student_one_login.json()['access_token']}"}
    registered = client.post("/api/v1/event-registrations/", json={"event_id": event.json()["id"]}, headers=student_one_headers)
    assert registered.status_code == 201
    assert registered.json()["status"] == "registered"

    student_two_login = client.post("/api/v1/auth/login", json={"email": "student_two_event_history@example.com", "password": "password123"})
    student_two_headers = {"Authorization": f"Bearer {student_two_login.json()['access_token']}"}
    waitlisted = client.post("/api/v1/event-registrations/", json={"event_id": event.json()["id"]}, headers=student_two_headers)
    assert waitlisted.status_code == 201
    assert waitlisted.json()["status"] == "waitlisted"

    history = client.get(
        f"/api/v1/event-registrations/history?event_id={event.json()['id']}",
        headers=coordinator_headers,
    )
    assert history.status_code == 200
    assert history.json()[0]["total"] == 1
    assert history.json()[0]["waitlisted"] == 1
    assert history.json()[0]["source_action"] == "create_event_registration"


def test_promoting_member_to_president_syncs_student_extension_scope() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_president_sync@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Future President",
            "email": "future_president@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "club_president_sync_coord@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert admin.status_code == 201
    assert student.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_president_sync@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Leadership Circle",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "status": "active",
            "membership_type": "open",
            "registration_open": True,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "future_president@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    join = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=student_headers)
    assert join.status_code == 200
    assert join.json()["status"] == "approved"

    members = client.get(f"/api/v1/clubs/{club.json()['id']}/members", headers=admin_headers)
    assert members.status_code == 200
    member = members.json()[0]

    promoted = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/members/{member['id']}",
        json={"role": "president"},
        headers=admin_headers,
    )
    assert promoted.status_code == 200
    assert promoted.json()["role"] == "president"

    stored_user = next(item for item in fake_db.users.items if str(item["_id"]) == student.json()["id"])
    assert "club_president" in stored_user.get("extended_roles", [])
    assert stored_user.get("role_scope", {}).get("club_president", {}).get("club_id") == club.json()["id"]

    stored_club = next(item for item in fake_db.clubs.items if str(item["_id"]) == club.json()["id"])
    assert stored_club.get("president_user_id") == student.json()["id"]


def test_student_extension_assignment_syncs_president_membership() -> None:
    fake_db = _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_extension_president_sync@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Scoped President",
            "email": "scoped_president@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "extension_president_sync_coord@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    assert admin.status_code == 201
    assert student.status_code == 201
    assert coordinator.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_extension_president_sync@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Governance Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "status": "active",
            "membership_type": "open",
            "registration_open": True,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    update = client.patch(
        f"/api/v1/users/{student.json()['id']}/extensions",
        json={
            "extended_roles": ["club_president"],
            "role_scope": {"club_president": {"club_id": club.json()["id"]}},
        },
        headers=admin_headers,
    )
    assert update.status_code == 200
    assert "club_president" in update.json()["extended_roles"]
    assert update.json()["role_scope"]["club_president"]["club_id"] == club.json()["id"]

    stored_club = next(item for item in fake_db.clubs.items if str(item["_id"]) == club.json()["id"])
    assert stored_club.get("president_user_id") == student.json()["id"]

    president_membership = next(
        item
        for item in fake_db.club_members.items
        if item.get("club_id") == club.json()["id"] and item.get("student_user_id") == student.json()["id"]
    )
    assert president_membership.get("role") == "president"
    assert president_membership.get("status") == "active"


def test_club_coordinator_and_president_can_publish_club_notice() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_notice_publish@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_notice_publish@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    president = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "President",
            "email": "president_club_notice_publish@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    outsider = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Outsider",
            "email": "outsider_club_notice_publish@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert president.status_code == 201
    assert outsider.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_notice_publish@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Writers Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "status": "active",
            "membership_type": "open",
            "registration_open": True,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    president_login = client.post(
        "/api/v1/auth/login",
        json={"email": "president_club_notice_publish@example.com", "password": "password123"},
    )
    president_headers = {"Authorization": f"Bearer {president_login.json()['access_token']}"}
    join = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=president_headers)
    assert join.status_code == 200

    members = client.get(f"/api/v1/clubs/{club.json()['id']}/members", headers=admin_headers)
    member_id = members.json()[0]["id"]
    promoted = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/members/{member_id}",
        json={"role": "president"},
        headers=admin_headers,
    )
    assert promoted.status_code == 200

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_notice_publish@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    coordinator_notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "Club Meeting",
            "message": "Coordinator update",
            "scope": "club",
            "scope_ref_id": club.json()["id"],
        },
        headers=coordinator_headers,
    )
    assert coordinator_notice.status_code == 201
    assert coordinator_notice.json()["scope"] == "club"

    president_notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "President Note",
            "message": "President update",
            "scope": "club",
            "scope_ref_id": club.json()["id"],
        },
        headers=president_headers,
    )
    assert president_notice.status_code == 201
    assert president_notice.json()["scope_ref_id"] == club.json()["id"]

    outsider_login = client.post(
        "/api/v1/auth/login",
        json={"email": "outsider_club_notice_publish@example.com", "password": "password123"},
    )
    outsider_headers = {"Authorization": f"Bearer {outsider_login.json()['access_token']}"}
    denied = client.post(
        "/api/v1/notices/",
        json={
            "title": "Fake Notice",
            "message": "Outsider update",
            "scope": "club",
            "scope_ref_id": club.json()["id"],
        },
        headers=outsider_headers,
    )
    assert denied.status_code == 403


def test_club_notice_visible_only_to_members_and_president() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_notice_visible@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_notice_visible@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    member = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Member",
            "email": "member_club_notice_visible@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    outsider = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Outsider",
            "email": "outsider_club_notice_visible@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert member.status_code == 201
    assert outsider.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_notice_visible@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Readers Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "status": "active",
            "membership_type": "open",
            "registration_open": True,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    member_login = client.post(
        "/api/v1/auth/login",
        json={"email": "member_club_notice_visible@example.com", "password": "password123"},
    )
    member_headers = {"Authorization": f"Bearer {member_login.json()['access_token']}"}
    join = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=member_headers)
    assert join.status_code == 200

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_notice_visible@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    notice = client.post(
        "/api/v1/notices/",
        json={
            "title": "Member-only Update",
            "message": "Club scoped message",
            "scope": "club",
            "scope_ref_id": club.json()["id"],
        },
        headers=coordinator_headers,
    )
    assert notice.status_code == 201

    visible_to_member = client.get(
        "/api/v1/notices/",
        params={"scope": "club", "scope_ref_id": club.json()["id"], "include_expired": True},
        headers=member_headers,
    )
    assert visible_to_member.status_code == 200
    assert [item["id"] for item in visible_to_member.json()] == [notice.json()["id"]]

    outsider_login = client.post(
        "/api/v1/auth/login",
        json={"email": "outsider_club_notice_visible@example.com", "password": "password123"},
    )
    outsider_headers = {"Authorization": f"Bearer {outsider_login.json()['access_token']}"}
    hidden_from_outsider = client.get(
        "/api/v1/notices/",
        params={"scope": "club", "scope_ref_id": club.json()["id"], "include_expired": True},
        headers=outsider_headers,
    )
    assert hidden_from_outsider.status_code == 200
    assert hidden_from_outsider.json() == []


def test_club_notice_moderation_supports_pin_and_archive_for_club_leads() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_notice_manage@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_club_notice_manage@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    president = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "President",
            "email": "president_club_notice_manage@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert president.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_notice_manage@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Moderation Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
            "status": "active",
            "membership_type": "open",
            "registration_open": True,
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    president_login = client.post(
        "/api/v1/auth/login",
        json={"email": "president_club_notice_manage@example.com", "password": "password123"},
    )
    president_headers = {"Authorization": f"Bearer {president_login.json()['access_token']}"}
    join = client.post(f"/api/v1/clubs/{club.json()['id']}/join", headers=president_headers)
    assert join.status_code == 200

    members = client.get(f"/api/v1/clubs/{club.json()['id']}/members", headers=admin_headers)
    member_id = members.json()[0]["id"]
    promoted = client.patch(
        f"/api/v1/clubs/{club.json()['id']}/members/{member_id}",
        json={"role": "president"},
        headers=admin_headers,
    )
    assert promoted.status_code == 200

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_club_notice_manage@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    created = client.post(
        "/api/v1/notices/",
        json={
            "title": "Pinned Candidate",
            "message": "Needs top placement",
            "scope": "club",
            "scope_ref_id": club.json()["id"],
            "template_key": "event_reminder",
        },
        headers=coordinator_headers,
    )
    assert created.status_code == 201
    assert created.json()["template_key"] == "event_reminder"

    pinned = client.patch(
        f"/api/v1/notices/{created.json()['id']}",
        json={"is_pinned": True},
        headers=president_headers,
    )
    assert pinned.status_code == 200
    assert pinned.json()["is_pinned"] is True

    archived = client.delete(
        f"/api/v1/notices/{created.json()['id']}",
        headers=president_headers,
    )
    assert archived.status_code == 200
    assert archived.json()["success"] is True

    visible = client.get(
        "/api/v1/notices/",
        params={"scope": "club", "scope_ref_id": club.json()["id"], "include_expired": True},
        headers=president_headers,
    )
    assert visible.status_code == 200
    assert visible.json() == []


def test_club_profile_fields_persist_across_create_and_update() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_club_profile@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    assert admin.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_club_profile@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}

    created = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Creative Club",
            "description": "Club profile test",
            "status": "draft",
            "tagline": "Design, build, and showcase bold campus work.",
            "achievement_highlights": ["Won design week", "Hosted 3 public demos"],
            "recruitment_headline": "Looking for makers, storytellers, and builders.",
            "recruitment_cta_label": "Join the intro circle",
            "public_contact_url": "https://example.com/creative-club",
        },
        headers=admin_headers,
    )
    assert created.status_code == 201
    assert created.json()["tagline"] == "Design, build, and showcase bold campus work."
    assert created.json()["achievement_highlights"] == ["Won design week", "Hosted 3 public demos"]

    updated = client.patch(
        f"/api/v1/clubs/{created.json()['id']}",
        json={
            "tagline": "Build ambitious campus projects together.",
            "achievement_highlights": ["Ran a 200-student hack sprint"],
            "recruitment_headline": "Recruiting students who want to ship work, not just discuss it.",
            "recruitment_cta_label": "See open roles",
            "public_contact_url": "https://example.com/creative-club/apply",
            "logo_url": "https://example.com/logo.png",
            "banner_url": "https://example.com/banner.png",
        },
        headers=admin_headers,
    )
    assert updated.status_code == 200
    assert updated.json()["tagline"] == "Build ambitious campus projects together."
    assert updated.json()["achievement_highlights"] == ["Ran a 200-student hack sprint"]
    assert updated.json()["recruitment_cta_label"] == "See open roles"
    assert updated.json()["public_contact_url"] == "https://example.com/creative-club/apply"
    assert updated.json()["logo_url"] == "https://example.com/logo.png"
    assert updated.json()["banner_url"] == "https://example.com/banner.png"


def test_club_coordinator_can_approve_registration_mark_attendance_and_issue_certificate() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_event_lifecycle@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_event_lifecycle@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Lifecycle",
            "email": "student_event_lifecycle@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_event_lifecycle@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Innovation Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_event_lifecycle@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Innovation Demo",
            "capacity": 25,
            "approval_required": True,
            "certificate_enabled": True,
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_event_lifecycle@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert registration.status_code == 201
    assert registration.json()["status"] == "pending"
    registration_id = registration.json()["id"]

    approved = client.patch(
        f"/api/v1/event-registrations/{registration_id}",
        json={"status": "approved"},
        headers=coordinator_headers,
    )
    assert approved.status_code == 200
    assert approved.json()["status"] == "approved"

    attendance = client.patch(
        f"/api/v1/event-registrations/{registration_id}",
        json={"attendance_status": "present"},
        headers=coordinator_headers,
    )
    assert attendance.status_code == 200
    assert attendance.json()["attendance_status"] == "present"

    certificate = client.patch(
        f"/api/v1/event-registrations/{registration_id}",
        json={"certificate_issued": True},
        headers=coordinator_headers,
    )
    assert certificate.status_code == 200
    assert certificate.json()["certificate_issued"] is True


def test_certificate_requires_present_attendance() -> None:
    _setup_fake_db()
    client = TestClient(app)

    admin = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Admin",
            "email": "admin_event_certificate_guard@example.com",
            "password": "password123",
            "role": "admin",
        },
    )
    coordinator = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Coordinator",
            "email": "coord_event_certificate_guard@example.com",
            "password": "password123",
            "role": "teacher",
        },
    )
    student = client.post(
        "/api/v1/auth/register",
        json={
            "full_name": "Student Guard",
            "email": "student_event_certificate_guard@example.com",
            "password": "password123",
            "role": "student",
        },
    )
    assert admin.status_code == 201
    assert coordinator.status_code == 201
    assert student.status_code == 201

    admin_login = client.post(
        "/api/v1/auth/login",
        json={"email": "admin_event_certificate_guard@example.com", "password": "password123"},
    )
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
    club = client.post(
        "/api/v1/clubs/",
        json={
            "name": "Coding Club",
            "description": "Club",
            "coordinator_user_id": coordinator.json()["id"],
        },
        headers=admin_headers,
    )
    assert club.status_code == 201

    coordinator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "coord_event_certificate_guard@example.com", "password": "password123"},
    )
    coordinator_headers = {"Authorization": f"Bearer {coordinator_login.json()['access_token']}"}
    event = client.post(
        "/api/v1/club-events/",
        json={
            "club_id": club.json()["id"],
            "title": "Hackathon",
            "capacity": 10,
            "approval_required": True,
            "certificate_enabled": True,
        },
        headers=coordinator_headers,
    )
    assert event.status_code == 201

    student_login = client.post(
        "/api/v1/auth/login",
        json={"email": "student_event_certificate_guard@example.com", "password": "password123"},
    )
    student_headers = {"Authorization": f"Bearer {student_login.json()['access_token']}"}
    registration = client.post(
        "/api/v1/event-registrations/",
        json={"event_id": event.json()["id"]},
        headers=student_headers,
    )
    assert registration.status_code == 201
    registration_id = registration.json()["id"]

    approved = client.patch(
        f"/api/v1/event-registrations/{registration_id}",
        json={"status": "approved"},
        headers=coordinator_headers,
    )
    assert approved.status_code == 200

    denied = client.patch(
        f"/api/v1/event-registrations/{registration_id}",
        json={"certificate_issued": True},
        headers=coordinator_headers,
    )
    assert denied.status_code == 400
    assert denied.json()["detail"] == "Attendance must be marked present before issuing a certificate"


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
    fake_db = _setup_fake_db()
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
    structure_seed = _seed_canonical_structure(fake_db, suffix="STRU", semester_number=3)
    class_item = client.post(
        "/api/v1/sections/",
        json=_create_section_payload(
            structure_seed,
            name="Computer Science Engineering",
            faculty_name="Faculty of Engineering",
            class_coordinator_user_id=teacher_owner.json()["id"],
        ),
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
    assert structure.json()["programs"] == []


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


