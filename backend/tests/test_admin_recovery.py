import asyncio

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

    def find(self, _query):
        return _Cursor(self.items)


class _DB:
    def __init__(self):
        self.departments = _Collection([{"_id": ObjectId(), "name": "Department A", "deleted_at": None, "is_active": False}])
        self.classes = _Collection([])
        self.notices = _Collection([])
        self.notifications = _Collection([])
        self.clubs = _Collection([])
        self.club_events = _Collection([])
        self.assignments = _Collection([])
        self.submissions = _Collection([])
        self.evaluations = _Collection([])
        self.review_tickets = _Collection([])
        self.courses = _Collection([{"_id": ObjectId(), "name": "Legacy Course", "deleted_at": None, "is_active": False}])
        self.branches = _Collection([])
        self.years = _Collection([])

    def __getitem__(self, name):
        return getattr(self, name)


def test_list_recovery_items_hides_legacy_collections_by_default(monkeypatch):
    monkeypatch.setattr(admin_recovery, "db", _DB())

    result = asyncio.run(
        admin_recovery.list_recovery_items(
            collection=None,
            include_legacy=False,
            limit=100,
            _current_user={"_id": str(ObjectId())},
        )
    )

    assert "departments" in result["items"]
    assert "courses" not in result["items"]
    assert result["legacy_collections_included"] is False


def test_list_recovery_items_includes_legacy_when_requested(monkeypatch):
    monkeypatch.setattr(admin_recovery, "db", _DB())

    result = asyncio.run(
        admin_recovery.list_recovery_items(
            collection=None,
            include_legacy=True,
            limit=100,
            _current_user={"_id": str(ObjectId())},
        )
    )

    assert "courses" in result["items"]
    assert result["summary"]["courses"] == 1
    assert result["legacy_collections_included"] is True
