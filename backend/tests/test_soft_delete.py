from app.core.soft_delete import (
    apply_is_active_filter,
    build_restore_update,
    build_soft_delete_update,
    build_soft_deleted_query,
    build_state_update,
)


def test_apply_is_active_filter_sets_expected_flag() -> None:
    query = {"code": "FOENG"}

    result = apply_is_active_filter(query, False)

    assert result is query
    assert query == {"code": "FOENG", "is_active": False}


def test_build_soft_delete_update_uses_canonical_fields() -> None:
    update = build_soft_delete_update(deleted_by="admin-1")

    assert update["$set"]["is_active"] is False
    assert update["$set"]["deleted_by"] == "admin-1"
    assert update["$set"]["deleted_at"] is not None
    assert "is_deleted" not in update["$set"]


def test_build_soft_deleted_query_prefers_deleted_at_and_supports_legacy_fallback() -> None:
    canonical = build_soft_deleted_query()
    legacy_aware = build_soft_deleted_query(include_legacy_marker=True)

    assert canonical == {"deleted_at": {"$ne": None}}
    assert legacy_aware["$or"][0] == {"deleted_at": {"$ne": None}}
    assert legacy_aware["$or"][1] == {
        "$and": [
            {"is_deleted": True},
            {"$or": [{"deleted_at": {"$exists": False}}, {"deleted_at": None}]},
        ]
    }


def test_build_restore_update_clears_delete_markers() -> None:
    update = build_restore_update(restored_by="admin-2")

    assert update["$set"]["is_active"] is True
    assert update["$set"]["restored_by"] == "admin-2"
    assert update["$set"]["restored_at"] is not None
    assert update["$unset"] == {"deleted_at": "", "deleted_by": "", "is_deleted": ""}


def test_build_state_update_clears_delete_markers_on_reactivation() -> None:
    update = build_state_update({"name": "Faculty of Engineering", "is_active": True})

    assert update["$set"] == {"name": "Faculty of Engineering", "is_active": True}
    assert update["$unset"] == {"deleted_at": "", "deleted_by": "", "is_deleted": ""}
