import asyncio
from types import SimpleNamespace

from bson import ObjectId
import pytest

from app.api.v1.endpoints import departments as departments_endpoint
from app.services import governance as governance_service


class _FakeDepartmentsCollection:
    def __init__(self, department):
        self.department = department
        self.update_one_query = None
        self.update_one_payload = None

    async def find_one(self, query):
        if query.get('_id') == self.department['_id']:
            return self.department
        return None

    async def update_one(self, query, update):
        self.update_one_query = query
        self.update_one_payload = update
        return SimpleNamespace(matched_count=1)


class _FakeBranchesCollection:
    def __init__(self):
        self.update_many_query = None
        self.update_many_payload = None

    async def update_many(self, query, update):
        self.update_many_query = query
        self.update_many_payload = update
        return SimpleNamespace(matched_count=1, modified_count=1)


class _FakeSettingsCollection:
    def __init__(self, value):
        self.value = value

    async def find_one(self, query):
        if query.get('key') == 'governance_policy':
            return {'key': 'governance_policy', 'value': self.value}
        return None


def test_delete_department_archives_department_and_related_branches(monkeypatch) -> None:
    department_id = ObjectId()
    user_id = ObjectId()
    department = {
        '_id': department_id,
        'name': 'Computer Science',
        'code': 'FOENG-D03',
        'is_active': True,
    }
    fake_departments = _FakeDepartmentsCollection(department)
    fake_branches = _FakeBranchesCollection()
    review_calls = []

    async def fake_enforce_review_approval(**kwargs):
        review_calls.append(kwargs)

    monkeypatch.setattr(
        departments_endpoint,
        'db',
        SimpleNamespace(
            departments=fake_departments,
            branches=fake_branches,
        ),
    )
    monkeypatch.setattr(departments_endpoint, 'enforce_review_approval', fake_enforce_review_approval)

    result = asyncio.run(
        departments_endpoint.delete_department(
            str(department_id),
            review_id='review-123',
            current_user={'_id': user_id, 'role': 'admin', 'admin_type': 'super_admin'},
        )
    )

    assert result == {'message': 'Department archived'}
    assert review_calls == [
        {
            'current_user': {'_id': user_id, 'role': 'admin', 'admin_type': 'super_admin'},
            'review_id': 'review-123',
            'action': 'departments.delete',
            'entity_type': 'department',
            'entity_id': str(department_id),
        }
    ]
    assert fake_branches.update_many_query == {'department_code': 'FOENG-D03'}
    assert fake_branches.update_many_payload['$set']['is_active'] is False
    assert fake_branches.update_many_payload['$set']['deleted_by'] == str(user_id)
    assert fake_branches.update_many_payload['$set']['deleted_at'] is not None
    assert fake_departments.update_one_query == {'_id': department_id, 'is_active': True}
    assert fake_departments.update_one_payload['$set']['is_active'] is False
    assert fake_departments.update_one_payload['$set']['deleted_by'] == str(user_id)
    assert fake_departments.update_one_payload['$set']['deleted_at'] is not None


def test_delete_department_requires_review_id_when_two_person_rule_enabled(monkeypatch) -> None:
    department_id = ObjectId()
    department = {
        '_id': department_id,
        'name': 'Mechanical Engineering',
        'code': 'FOENG-D02',
        'is_active': True,
    }
    fake_departments = _FakeDepartmentsCollection(department)
    fake_branches = _FakeBranchesCollection()

    monkeypatch.setattr(
        departments_endpoint,
        'db',
        SimpleNamespace(
            departments=fake_departments,
            branches=fake_branches,
        ),
    )
    monkeypatch.setattr(
        governance_service,
        'db',
        SimpleNamespace(settings=_FakeSettingsCollection({'two_person_rule_enabled': True})),
    )

    with pytest.raises(Exception) as exc_info:
        asyncio.run(
            departments_endpoint.delete_department(
                str(department_id),
                review_id=None,
                current_user={'_id': ObjectId(), 'role': 'admin', 'admin_type': 'super_admin'},
            )
        )

    error = exc_info.value
    assert getattr(error, 'status_code', None) == 403
    assert 'review_id' in str(getattr(error, 'detail', '')).lower()
    assert fake_branches.update_many_query is None
    assert fake_departments.update_one_query is None
