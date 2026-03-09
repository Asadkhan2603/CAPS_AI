import asyncio
from types import SimpleNamespace

from bson import ObjectId
import pytest

from app.api.v1.endpoints import departments as departments_endpoint
from app.services import governance as governance_service


class _FakeDepartmentsCollection:
    def __init__(self, department):
        self.department = department

    async def find_one(self, query):
        if query.get("_id") == self.department["_id"]:
            return self.department
        return None

    async def update_one(self, query, update):
        return SimpleNamespace(matched_count=1)


class _FakeBranchesCollection:
    async def update_many(self, query, update):
        return SimpleNamespace(matched_count=1, modified_count=1)


class _FakeSettingsCollection:
    def __init__(self, value):
        self.value = value

    async def find_one(self, query):
        if query.get("key") == "governance_policy":
            return {"key": "governance_policy", "value": self.value}
        return None


class _FakeReviewsCollection:
    def __init__(self, review):
        self.review = review
        self.updated = None

    async def find_one(self, query):
        if query.get("_id") == self.review["_id"]:
            return self.review
        return None

    async def update_one(self, query, update):
        self.updated = {"query": query, "update": update}
        for key, value in update.get("$set", {}).items():
            self.review[key] = value
        return SimpleNamespace(matched_count=1, modified_count=1)


def test_delete_department_emits_requested_and_completed_telemetry(monkeypatch) -> None:
    department_id = ObjectId()
    user_id = ObjectId()
    telemetry_calls = []

    async def fake_log_destructive_action_event(**kwargs):
        telemetry_calls.append(kwargs)
        return kwargs

    async def fake_enforce_review_approval(**kwargs):
        return True

    monkeypatch.setattr(
        departments_endpoint,
        "db",
        SimpleNamespace(
            departments=_FakeDepartmentsCollection(
                {
                    "_id": department_id,
                    "name": "Computer Science",
                    "code": "FOENG-D03",
                    "is_active": True,
                }
            ),
            branches=_FakeBranchesCollection(),
        ),
    )
    monkeypatch.setattr(departments_endpoint, "log_destructive_action_event", fake_log_destructive_action_event)
    monkeypatch.setattr(departments_endpoint, "enforce_review_approval", fake_enforce_review_approval)

    result = asyncio.run(
        departments_endpoint.delete_department(
            str(department_id),
            review_id="review-123",
            current_user={"_id": user_id, "role": "admin", "admin_type": "super_admin"},
        )
    )

    assert result == {"message": "Department archived"}
    assert telemetry_calls[0]["stage"] == "requested"
    assert telemetry_calls[0]["review_id"] == "review-123"
    assert telemetry_calls[0]["actor_user_id"] == str(user_id)
    assert telemetry_calls[1]["stage"] == "completed"
    assert telemetry_calls[1]["governance_completed"] is True
    assert telemetry_calls[1]["outcome"] == "archived"


def test_enforce_review_approval_logs_blocked_when_review_id_missing(monkeypatch) -> None:
    telemetry_calls = []

    async def fake_log_destructive_action_event(**kwargs):
        telemetry_calls.append(kwargs)
        return kwargs

    monkeypatch.setattr(governance_service, "log_destructive_action_event", fake_log_destructive_action_event)
    monkeypatch.setattr(
        governance_service,
        "db",
        SimpleNamespace(settings=_FakeSettingsCollection({"two_person_rule_enabled": True})),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            governance_service.enforce_review_approval(
                current_user={"_id": ObjectId(), "role": "admin", "admin_type": "super_admin"},
                review_id=None,
                action="departments.delete",
                entity_type="department",
                entity_id="department-1",
            )
        )

    error = exc_info.value
    assert getattr(error, "status_code", None) == 403
    assert telemetry_calls == [
        {
            "actor_user_id": telemetry_calls[0]["actor_user_id"],
            "action": "departments.delete",
            "entity_type": "department",
            "entity_id": "department-1",
            "stage": "governance_blocked",
            "detail": "Governance approval required but review_id missing",
            "review_id": None,
            "governance_required": True,
            "governance_completed": False,
            "outcome": "blocked",
            "metadata": {
                "review_type": "destructive",
                "review_status": "missing_review_id",
                "admin_type": "super_admin",
            },
            "severity": "high",
        }
    ]


def test_enforce_review_approval_logs_governance_completed(monkeypatch) -> None:
    review_id = ObjectId()
    requested_by = str(ObjectId())
    current_user_id = ObjectId()
    telemetry_calls = []
    reviews = _FakeReviewsCollection(
        {
            "_id": review_id,
            "status": "approved",
            "requested_by": requested_by,
            "review_type": "destructive",
            "action": "departments.delete",
            "entity_type": "department",
            "entity_id": "department-1",
        }
    )

    async def fake_log_destructive_action_event(**kwargs):
        telemetry_calls.append(kwargs)
        return kwargs

    monkeypatch.setattr(governance_service, "log_destructive_action_event", fake_log_destructive_action_event)
    monkeypatch.setattr(
        governance_service,
        "db",
        SimpleNamespace(
            settings=_FakeSettingsCollection({"two_person_rule_enabled": True}),
            admin_action_reviews=reviews,
        ),
    )

    result = asyncio.run(
        governance_service.enforce_review_approval(
            current_user={"_id": current_user_id, "role": "admin", "admin_type": "super_admin"},
            review_id=str(review_id),
            action="departments.delete",
            entity_type="department",
            entity_id="department-1",
        )
    )

    assert result is True
    assert reviews.updated is not None
    assert reviews.review["status"] == "executed"
    assert telemetry_calls == [
        {
            "actor_user_id": str(current_user_id),
            "action": "departments.delete",
            "entity_type": "department",
            "entity_id": "department-1",
            "stage": "governance_completed",
            "detail": "Governance review executed for destructive action",
            "review_id": str(review_id),
            "governance_required": True,
            "governance_completed": True,
            "outcome": "approved",
            "metadata": {
                "review_type": "destructive",
                "review_status": "executed",
                "admin_type": "super_admin",
            },
            "severity": "medium",
        }
    ]
