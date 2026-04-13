import asyncio
from datetime import datetime, timezone

from bson import ObjectId

from app.api.v1.endpoints import admin_recovery


class _Cursor:
    def __init__(self, items):
        self.items = list(items)
        self._limit = None

    def limit(self, amount):
        self._limit = amount
        return self

    async def to_list(self, length):
        scoped = self.items[: self._limit] if self._limit is not None else self.items
        return scoped[:length]


class _Collection:
    def __init__(self, items=None):
        self.items = list(items or [])
        self.inserted = []
        self.updated = []

    def find(self, _query, _projection=None):
        return _Cursor(self.items)

    async def find_one(self, query):
        for item in self.items:
            if item.get('_id') == query.get('_id'):
                return item
        return None

    async def update_one(self, query, update):
        self.updated.append((query, update))
        for item in self.items:
            if item.get('_id') == query.get('_id'):
                set_values = update.get('$set', {})
                unset_values = update.get('$unset', {})
                item.update(set_values)
                for key in unset_values:
                    item.pop(key, None)
                return

    async def insert_one(self, payload):
        self.inserted.append(payload)


class _DB:
    def __init__(self, *, department_deleted_by, course_deleted_by):
        department_id = ObjectId()
        course_id = ObjectId()
        self.departments = _Collection([
            {
                '_id': department_id,
                'name': 'Department A',
                'deleted_at': datetime(2026, 4, 12, 10, 30, tzinfo=timezone.utc),
                'deleted_by': department_deleted_by,
                'is_active': False,
                'code': 'DPT-A',
            }
        ])
        self.classes = _Collection([])
        self.notices = _Collection([])
        self.notifications = _Collection([])
        self.clubs = _Collection([])
        self.club_events = _Collection([])
        self.assignments = _Collection([])
        self.submissions = _Collection([])
        self.evaluations = _Collection([])
        self.review_tickets = _Collection([])
        self.courses = _Collection([
            {
                '_id': course_id,
                'name': 'Legacy Course',
                'deleted_at': datetime(2026, 4, 11, 9, 0, tzinfo=timezone.utc),
                'deleted_by': course_deleted_by,
                'is_active': False,
                'status': 'archived',
            }
        ])
        self.branches = _Collection([])
        self.years = _Collection([])
        self.users = _Collection([
            {
                '_id': ObjectId(department_deleted_by),
                'full_name': 'Admin One',
                'email': 'admin.one@caps.ai',
            }
        ])
        self.recovery_logs = _Collection([])

    def __getitem__(self, name):
        return getattr(self, name)


def test_list_recovery_items_hides_legacy_collections_by_default(monkeypatch):
    deleted_by = str(ObjectId())
    monkeypatch.setattr(admin_recovery, 'db', _DB(department_deleted_by=deleted_by, course_deleted_by=str(ObjectId())))

    result = asyncio.run(
        admin_recovery.list_recovery_items(
            collection=None,
            include_legacy=False,
            limit=100,
            _current_user={'_id': str(ObjectId())},
        )
    )

    assert 'departments' in result['items']
    assert 'courses' not in result['items']
    assert result['legacy_collections_included'] is False
    assert result['catalog'][0] == {
        'key': 'departments',
        'label': 'Departments',
        'legacy': False,
        'group': 'Academic structure',
    }
    row = result['items']['departments'][0]
    assert row['display_name'] == 'Department A'
    assert row['subtitle'] == 'DPT-A'
    assert row['status_label'] == 'Inactive'
    assert row['deleted_by_label'] == 'Admin One (admin.one@caps.ai)'
    assert row['audit_resource_type'] == 'departments'


def test_list_recovery_items_includes_legacy_when_requested(monkeypatch):
    deleted_by = str(ObjectId())
    monkeypatch.setattr(admin_recovery, 'db', _DB(department_deleted_by=str(ObjectId()), course_deleted_by=deleted_by))

    result = asyncio.run(
        admin_recovery.list_recovery_items(
            collection=None,
            include_legacy=True,
            limit=100,
            _current_user={'_id': str(ObjectId())},
        )
    )

    assert 'courses' in result['items']
    assert result['summary']['courses'] == 1
    assert result['legacy_collections_included'] is True
    assert any(item['key'] == 'courses' and item['legacy'] is True and item['group'] == 'Legacy' for item in result['catalog'])
    row = result['items']['courses'][0]
    assert row['display_name'] == 'Legacy Course'
    assert row['subtitle'] == 'Status: Archived'
    assert row['status_label'] == 'Archived'
    assert row['deleted_by_label'] == deleted_by


def test_restore_item_keeps_existing_contract_and_logs_audit(monkeypatch):
    current_user_id = str(ObjectId())
    deleted_by = str(ObjectId())
    fake_db = _DB(department_deleted_by=deleted_by, course_deleted_by=str(ObjectId()))
    monkeypatch.setattr(admin_recovery, 'db', fake_db)

    logged = {}

    async def _fake_log_audit_event(**payload):
        logged.update(payload)
        return payload

    monkeypatch.setattr(admin_recovery, 'log_audit_event', _fake_log_audit_event)

    row_id = str(fake_db.departments.items[0]['_id'])
    result = asyncio.run(
        admin_recovery.restore_item(
            collection='departments',
            item_id=row_id,
            current_user={'_id': current_user_id},
        )
    )

    assert result == {
        'success': True,
        'collection': 'departments',
        'id': row_id,
        'message': 'Item restored',
    }
    assert fake_db.departments.updated
    assert logged['action'] == 'restore'
    assert logged['entity_type'] == 'departments'
    assert logged['entity_id'] == row_id
    assert fake_db.recovery_logs.inserted[0]['collection'] == 'departments'
    assert fake_db.recovery_logs.inserted[0]['entity_id'] == row_id
