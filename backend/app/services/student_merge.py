from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Iterable

from bson import ObjectId
from fastapi import HTTPException, status

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import STUDENT_SCHEMA_VERSION
from app.services.public_ids import build_public_id, persist_public_id_update

PROFILE_FIELDS = ("full_name", "roll_number", "email", "user_id", "class_id", "group_id")


def _normalize_text(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _normalize_email(value: Any) -> str | None:
    text = _normalize_text(value)
    return text.lower() if text else None


def _case_id(student_ids: Iterable[str]) -> str:
    digest = hashlib.sha1(",".join(sorted(student_ids)).encode("utf-8")).hexdigest()[:12]
    return f"dup-case-{digest}"


def _student_sort_key(student: dict[str, Any]) -> tuple[int, int, int, int, str]:
    created_at = student.get("created_at")
    created_at_score = int(created_at.timestamp()) if hasattr(created_at, "timestamp") else 0
    roll_number = _normalize_text(student.get("roll_number")) or ""
    return (
        1 if _normalize_text(student.get("user_id")) else 0,
        1 if _normalize_text(student.get("class_id")) else 0,
        1 if bool(student.get("is_active", True)) else 0,
        created_at_score,
        "0" if not roll_number.startswith("USR-") else "1",
    )


def _student_member(student: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(student.get("_id")),
        "full_name": student.get("full_name") or "",
        "roll_number": student.get("roll_number"),
        "email": student.get("email"),
        "user_id": student.get("user_id"),
        "class_id": student.get("class_id"),
        "group_id": student.get("group_id"),
        "is_active": bool(student.get("is_active", True)),
        "created_at": student.get("created_at"),
    }


def _match_keys(student: dict[str, Any]) -> list[tuple[str, str]]:
    keys: list[tuple[str, str]] = []
    roll_number = _normalize_text(student.get("roll_number"))
    email = _normalize_email(student.get("email"))
    user_id = _normalize_text(student.get("user_id"))
    if roll_number:
        keys.append(("roll_number", roll_number.lower()))
    if email:
        keys.append(("email", email))
    if user_id:
        keys.append(("user_id", user_id))
    return keys


def _conflicts(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    conflicts: list[dict[str, Any]] = []
    for field_name in PROFILE_FIELDS:
        buckets: dict[str, dict[str, Any]] = {}
        for member in members:
            raw_value = member.get(field_name)
            if field_name == "email":
                raw_value = _normalize_email(raw_value)
            else:
                raw_value = _normalize_text(raw_value)
            bucket_key = raw_value or "__empty__"
            bucket = buckets.setdefault(bucket_key, {"value": raw_value, "student_ids": []})
            bucket["student_ids"].append(str(member.get("_id")))
        unique_values = [bucket for bucket in buckets.values() if bucket.get("value")]
        if len(unique_values) > 1:
            conflicts.append(
                {
                    "field": field_name,
                    "values": unique_values,
                }
            )
    return conflicts


def _draft_resolved_profile(primary: dict[str, Any], members: list[dict[str, Any]]) -> dict[str, Any]:
    ranked_members = sorted(members, key=_student_sort_key, reverse=True)
    resolved: dict[str, Any] = {}
    for field_name in PROFILE_FIELDS:
        primary_value = primary.get(field_name)
        if field_name == "email":
            primary_value = _normalize_email(primary_value)
        else:
            primary_value = _normalize_text(primary_value)
        if primary_value:
            resolved[field_name] = primary_value
            continue
        fallback = None
        for member in ranked_members:
            candidate = member.get(field_name)
            if field_name == "email":
                candidate = _normalize_email(candidate)
            else:
                candidate = _normalize_text(candidate)
            if candidate:
                fallback = candidate
                break
        resolved[field_name] = fallback
    return resolved


async def _existing_students(*, database: Any = db) -> list[dict[str, Any]]:
    return await database.students.find({}, {"full_name": 1, "roll_number": 1, "email": 1, "user_id": 1, "class_id": 1, "group_id": 1, "is_active": 1, "created_at": 1, "public_id": 1}).to_list(length=5000)


def _duplicate_components(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    by_id = {str(row.get("_id")): row for row in rows if row.get("_id")}
    neighbors: dict[str, set[str]] = {student_id: set() for student_id in by_id}
    key_to_student_ids: dict[tuple[str, str], list[str]] = {}
    for row in rows:
        student_id = str(row.get("_id") or "").strip()
        if not student_id:
            continue
        for key in _match_keys(row):
            key_to_student_ids.setdefault(key, []).append(student_id)

    for student_ids in key_to_student_ids.values():
        if len(student_ids) < 2:
            continue
        unique_ids = list(dict.fromkeys(student_ids))
        for student_id in unique_ids:
            neighbors[student_id].update(other_id for other_id in unique_ids if other_id != student_id)

    components: list[list[dict[str, Any]]] = []
    visited: set[str] = set()
    for student_id, linked_ids in neighbors.items():
        if student_id in visited or not linked_ids:
            continue
        stack = [student_id]
        component_ids: list[str] = []
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component_ids.append(current)
            stack.extend(neighbors.get(current, set()) - visited)
        if len(component_ids) > 1:
            components.append([by_id[current] for current in component_ids if current in by_id])
    return components


async def _count_documents(collection: Any, query: dict[str, Any]) -> int:
    if collection is None:
        return 0
    counter = getattr(collection, "count_documents", None)
    if callable(counter):
        return int(await counter(query))
    rows = await collection.find(query).to_list(length=5000)
    return len(rows)


async def _reference_counts(
    *,
    database: Any,
    primary_student_id: str,
    members: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    losing_ids = [str(member.get("_id")) for member in members if str(member.get("_id")) != primary_student_id]
    losing_rolls = [
        _normalize_text(member.get("roll_number"))
        for member in members
        if str(member.get("_id")) != primary_student_id and _normalize_text(member.get("roll_number"))
    ]
    if not losing_ids and not losing_rolls:
        return []

    queries = [
        ("enrollments", {"student_id": {"$in": [*losing_ids, *losing_rolls]}}),
        ("attendance_records", {"student_id": {"$in": losing_ids}}),
        ("internship_sessions", {"student_id": {"$in": losing_ids}}),
        ("grievances", {"student_id": {"$in": losing_ids}}),
        ("student_interventions", {"student_id": {"$in": losing_ids}}),
    ]
    counts: list[dict[str, Any]] = []
    for collection_name, query in queries:
        count = await _count_documents(getattr(database, collection_name, None), query)
        if count:
            counts.append({"collection": collection_name, "count": count})
    return counts


async def _build_case(
    members: list[dict[str, Any]],
    *,
    preferred_primary_student_id: str | None = None,
    database: Any = db,
) -> dict[str, Any]:
    sorted_members = sorted(members, key=_student_sort_key, reverse=True)
    member_ids = [str(member.get("_id")) for member in sorted_members]
    primary = next(
        (member for member in sorted_members if str(member.get("_id")) == preferred_primary_student_id),
        sorted_members[0],
    )
    matched_by = sorted({key_type for member in members for key_type, _ in _match_keys(member)})
    return {
        "case_id": _case_id(member_ids),
        "member_student_ids": member_ids,
        "matched_by": matched_by,
        "members": [_student_member(member) for member in sorted_members],
        "suggested_primary_student_id": str(primary.get("_id")),
        "conflicts": _conflicts(members),
        "reference_counts": await _reference_counts(
            database=database,
            primary_student_id=str(primary.get("_id")),
            members=members,
        ),
    }


async def list_duplicate_cases(*, database: Any = db, limit: int = 25) -> list[dict[str, Any]]:
    rows = await _existing_students(database=database)
    components = _duplicate_components(rows)
    cases = [await _build_case(component, database=database) for component in components]
    cases.sort(
        key=lambda item: (
            -len(item.get("member_student_ids", [])),
            -sum(entry.get("count", 0) for entry in item.get("reference_counts", [])),
            item.get("case_id", ""),
        )
    )
    return cases[:limit]


async def _students_by_ids(student_ids: Iterable[str], *, database: Any = db) -> list[dict[str, Any]]:
    normalized_ids = [str(student_id).strip() for student_id in student_ids if str(student_id or "").strip()]
    unique_ids: list[str] = list(dict.fromkeys(normalized_ids))
    if not unique_ids:
        return []
    object_ids = [parse_object_id(student_id) for student_id in unique_ids]
    rows = await database.students.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    rows_by_id = {str(row.get("_id")): row for row in rows}
    return [rows_by_id[student_id] for student_id in unique_ids if student_id in rows_by_id]


async def preview_merge_case(
    *,
    seed_student_ids: list[str],
    preferred_primary_student_id: str | None = None,
    database: Any = db,
) -> dict[str, Any]:
    rows = await _existing_students(database=database)
    requested_ids = {str(student_id).strip() for student_id in seed_student_ids if str(student_id or "").strip()}
    if not requested_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="seed_student_ids is required")

    component = next(
        (item for item in _duplicate_components(rows) if requested_ids & {str(member.get("_id")) for member in item}),
        None,
    )
    if component is None or len(component) < 2:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Duplicate case not found")
    component_ids = {str(member.get("_id")) for member in component}
    if not requested_ids.issubset(component_ids):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="All requested student ids must belong to the same duplicate case")

    case = await _build_case(component, preferred_primary_student_id=preferred_primary_student_id, database=database)
    primary_id = case["suggested_primary_student_id"]
    primary = next(member for member in component if str(member.get("_id")) == primary_id)
    resolved_profile = _draft_resolved_profile(primary, component)
    hard_delete_ids = [student_id for student_id in case["member_student_ids"] if student_id != primary_id]
    warnings: list[str] = []
    if any(not member.get("is_active", True) for member in case["members"]):
        warnings.append("This merge includes inactive student profiles.")
    if any(entry.get("collection") == "enrollments" for entry in case["reference_counts"]):
        warnings.append("Legacy enrollment references will be normalized to the canonical student id.")
    return {
        **case,
        "resolved_profile": resolved_profile,
        "hard_delete_ids": hard_delete_ids,
        "warnings": warnings,
    }


async def _validate_resolved_profile(
    resolved_profile: dict[str, Any],
    *,
    database: Any = db,
) -> dict[str, Any]:
    normalized = {
        "full_name": _normalize_text(resolved_profile.get("full_name")),
        "roll_number": _normalize_text(resolved_profile.get("roll_number")),
        "email": _normalize_email(resolved_profile.get("email")),
        "user_id": _normalize_text(resolved_profile.get("user_id")),
        "class_id": _normalize_text(resolved_profile.get("class_id")),
        "group_id": _normalize_text(resolved_profile.get("group_id")),
        "is_active": bool(resolved_profile.get("is_active", True)),
    }
    if not normalized["full_name"] or not normalized["roll_number"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resolved profile must include full_name and roll_number")

    class_doc = None
    if normalized["class_id"]:
        class_doc = await database.classes.find_one({"_id": parse_object_id(normalized["class_id"])})
        if not class_doc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Class not found for resolved class_id")

    if normalized["group_id"]:
        group_doc = await database.groups.find_one({"_id": parse_object_id(normalized["group_id"]), "is_active": True})
        if not group_doc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Group not found for resolved group_id")
        if normalized["class_id"] and group_doc.get("section_id") != normalized["class_id"]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resolved group_id does not belong to resolved class_id")
        if not normalized["class_id"]:
            normalized["class_id"] = _normalize_text(group_doc.get("section_id"))
            class_doc = group_doc

    if normalized["user_id"]:
        user = await database.users.find_one({"_id": parse_object_id(normalized["user_id"]), "role": "student", "is_active": True})
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Resolved user_id must reference an active student user")

    return normalized


async def _ensure_no_external_profile_conflicts(
    *,
    primary_student_id: str,
    member_student_ids: set[str],
    resolved_profile: dict[str, Any],
    database: Any = db,
) -> None:
    checks = [
        ("roll_number", resolved_profile.get("roll_number")),
        ("email", resolved_profile.get("email")),
        ("user_id", resolved_profile.get("user_id")),
    ]
    for field_name, value in checks:
        normalized_value = _normalize_email(value) if field_name == "email" else _normalize_text(value)
        if not normalized_value:
            continue
        rows = await database.students.find({field_name: normalized_value, "is_active": True}).to_list(length=20)
        for row in rows:
            row_id = str(row.get("_id"))
            if row_id in member_student_ids:
                continue
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Resolved {field_name} conflicts with another active student profile",
            )


def _sort_by_latest(*fields: str):
    def _score(row: dict[str, Any]) -> tuple[int, str]:
        for field_name in fields:
            value = row.get(field_name)
            if hasattr(value, "timestamp"):
                return (int(value.timestamp()), str(row.get("_id") or ""))
        created_at = datetime.now(timezone.utc)
        return (int(created_at.timestamp()), str(row.get("_id") or ""))

    return _score


async def _rewrite_enrollments(
    *,
    primary_student_id: str,
    losing_student_ids: list[str],
    losing_roll_numbers: list[str],
    final_roll_number: str,
    database: Any = db,
) -> dict[str, int]:
    collection = getattr(database, "enrollments", None)
    if collection is None:
        return {"rewritten": 0, "deleted": 0}

    rows = await collection.find({"student_id": {"$in": [primary_student_id, *losing_student_ids, *losing_roll_numbers]}}).to_list(length=5000)
    if not rows:
        return {"rewritten": 0, "deleted": 0}

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("class_id") or ""), []).append(row)

    rewritten = 0
    deleted = 0
    for class_id, items in grouped.items():
        keeper = next((item for item in items if str(item.get("student_id")) == primary_student_id), None)
        if keeper is None:
            keeper = sorted(items, key=_sort_by_latest("created_at"), reverse=True)[0]

        set_payload = {}
        if str(keeper.get("student_id")) != primary_student_id:
            set_payload["student_id"] = primary_student_id
        if final_roll_number and keeper.get("student_roll_number") != final_roll_number:
            set_payload["student_roll_number"] = final_roll_number
        if set_payload:
            await collection.update_one({"_id": keeper["_id"]}, {"$set": set_payload})
            rewritten += 1

        duplicate_ids = [item["_id"] for item in items if item.get("_id") != keeper.get("_id")]
        if duplicate_ids:
            result = await collection.delete_many({"_id": {"$in": duplicate_ids}})
            deleted += int(result.deleted_count)
    return {"rewritten": rewritten, "deleted": deleted}


async def _rewrite_attendance_records(
    *,
    primary_student_id: str,
    losing_student_ids: list[str],
    database: Any = db,
) -> dict[str, int]:
    collection = getattr(database, "attendance_records", None)
    if collection is None:
        return {"rewritten": 0, "deleted": 0}

    rows = await collection.find({"student_id": {"$in": [primary_student_id, *losing_student_ids]}}).to_list(length=5000)
    if not rows:
        return {"rewritten": 0, "deleted": 0}

    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row.get("class_slot_id") or ""), []).append(row)

    rewritten = 0
    deleted = 0
    for class_slot_id, items in grouped.items():
        keeper = next((item for item in items if str(item.get("student_id")) == primary_student_id), None)
        if keeper is None:
            keeper = sorted(items, key=_sort_by_latest("marked_at"), reverse=True)[0]

        if str(keeper.get("student_id")) != primary_student_id:
            public_id = build_public_id("attendance_record", {**keeper, "student_id": primary_student_id}, prefer_existing=False)
            update_payload = {"student_id": primary_student_id}
            if public_id:
                update_payload["public_id"] = public_id
            await collection.update_one({"_id": keeper["_id"]}, {"$set": update_payload})
            rewritten += 1

        duplicate_ids = [item["_id"] for item in items if item.get("_id") != keeper.get("_id")]
        if duplicate_ids:
            result = await collection.delete_many({"_id": {"$in": duplicate_ids}})
            deleted += int(result.deleted_count)
    return {"rewritten": rewritten, "deleted": deleted}


async def _rewrite_simple_student_id_collection(
    *,
    collection_name: str,
    primary_student_id: str,
    losing_student_ids: list[str],
    set_payload: dict[str, Any] | None = None,
    database: Any = db,
) -> dict[str, int]:
    collection = getattr(database, collection_name, None)
    if collection is None:
        return {"rewritten": 0, "deleted": 0}
    payload = {"student_id": primary_student_id, **(set_payload or {})}
    result = await collection.update_many({"student_id": {"$in": losing_student_ids}}, {"$set": payload})
    return {"rewritten": int(result.modified_count), "deleted": 0}


async def _verify_orphans(
    *,
    losing_student_ids: list[str],
    losing_roll_numbers: list[str],
    database: Any = db,
) -> list[str]:
    queries = [
        ("enrollments", {"student_id": {"$in": [*losing_student_ids, *losing_roll_numbers]}}),
        ("attendance_records", {"student_id": {"$in": losing_student_ids}}),
        ("internship_sessions", {"student_id": {"$in": losing_student_ids}}),
        ("grievances", {"student_id": {"$in": losing_student_ids}}),
        ("student_interventions", {"student_id": {"$in": losing_student_ids}}),
    ]
    remaining: list[str] = []
    for collection_name, query in queries:
        count = await _count_documents(getattr(database, collection_name, None), query)
        if count:
            remaining.append(collection_name)
    return remaining


async def execute_student_merge(
    *,
    primary_student_id: str,
    duplicate_student_ids: list[str],
    resolved_profile: dict[str, Any],
    actor_user_id: str,
    reason: str,
    database: Any = db,
) -> dict[str, Any]:
    normalized_primary_id = str(primary_student_id or "").strip()
    if not normalized_primary_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="primary_student_id is required")

    requested_ids = {normalized_primary_id, *[str(student_id).strip() for student_id in duplicate_student_ids if str(student_id or "").strip()]}
    preview = await preview_merge_case(
        seed_student_ids=sorted(requested_ids),
        preferred_primary_student_id=normalized_primary_id,
        database=database,
    )
    case_member_ids = set(preview["member_student_ids"])
    if requested_ids != case_member_ids:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Merge request must include the full duplicate case")

    if not preview["hard_delete_ids"]:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one duplicate student_id is required")

    normalized_profile = await _validate_resolved_profile(resolved_profile, database=database)
    await _ensure_no_external_profile_conflicts(
        primary_student_id=normalized_primary_id,
        member_student_ids=case_member_ids,
        resolved_profile=normalized_profile,
        database=database,
    )

    members = await _students_by_ids(sorted(case_member_ids), database=database)
    if len(members) != len(case_member_ids):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="One or more student profiles no longer exist")

    primary = next((member for member in members if str(member.get("_id")) == normalized_primary_id), None)
    if primary is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Primary student not found")

    losing_members = [member for member in members if str(member.get("_id")) != normalized_primary_id]
    losing_ids = [str(member.get("_id")) for member in losing_members]
    losing_roll_numbers = [_normalize_text(member.get("roll_number")) for member in losing_members if _normalize_text(member.get("roll_number"))]

    delayed_user_id = None
    if normalized_profile.get("user_id") and normalized_profile.get("user_id") != _normalize_text(primary.get("user_id")):
        if any(_normalize_text(member.get("user_id")) == normalized_profile["user_id"] for member in losing_members):
            delayed_user_id = normalized_profile["user_id"]

    immediate_profile = dict(normalized_profile)
    if delayed_user_id:
        immediate_profile["user_id"] = _normalize_text(primary.get("user_id"))

    update_payload = {**immediate_profile, "schema_version": STUDENT_SCHEMA_VERSION}
    persist_public_id_update(primary, update_payload, kind="student")
    await database.students.update_one({"_id": parse_object_id(normalized_primary_id)}, {"$set": update_payload})

    rewrite_map = {
        "enrollments": await _rewrite_enrollments(
            primary_student_id=normalized_primary_id,
            losing_student_ids=losing_ids,
            losing_roll_numbers=losing_roll_numbers,
            final_roll_number=normalized_profile["roll_number"],
            database=database,
        ),
        "attendance_records": await _rewrite_attendance_records(
            primary_student_id=normalized_primary_id,
            losing_student_ids=losing_ids,
            database=database,
        ),
        "internship_sessions": await _rewrite_simple_student_id_collection(
            collection_name="internship_sessions",
            primary_student_id=normalized_primary_id,
            losing_student_ids=losing_ids,
            database=database,
        ),
        "grievances": await _rewrite_simple_student_id_collection(
            collection_name="grievances",
            primary_student_id=normalized_primary_id,
            losing_student_ids=losing_ids,
            set_payload={
                "student_name": normalized_profile["full_name"],
                "student_email": normalized_profile["email"],
            },
            database=database,
        ),
        "student_interventions": await _rewrite_simple_student_id_collection(
            collection_name="student_interventions",
            primary_student_id=normalized_primary_id,
            losing_student_ids=losing_ids,
            set_payload={"student_name": normalized_profile["full_name"]},
            database=database,
        ),
    }

    remaining = await _verify_orphans(
        losing_student_ids=losing_ids,
        losing_roll_numbers=losing_roll_numbers,
        database=database,
    )
    if remaining:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Merge verification failed; unresolved references remain in {', '.join(sorted(remaining))}",
        )

    delete_result = await database.students.delete_many({"_id": {"$in": [parse_object_id(student_id) for student_id in losing_ids]}})
    if int(delete_result.deleted_count) != len(losing_ids):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Unable to delete all duplicate student profiles")

    if delayed_user_id:
        delayed_update = {"user_id": delayed_user_id, "schema_version": STUDENT_SCHEMA_VERSION}
        current_primary = await database.students.find_one({"_id": parse_object_id(normalized_primary_id)})
        persist_public_id_update(current_primary or primary, delayed_update, kind="student")
        await database.students.update_one({"_id": parse_object_id(normalized_primary_id)}, {"$set": delayed_update})

    merged = await database.students.find_one({"_id": parse_object_id(normalized_primary_id)})
    rewrite_counts = [
        {
            "collection": collection_name,
            "count": metrics.get("rewritten", 0) + metrics.get("deleted", 0),
        }
        for collection_name, metrics in rewrite_map.items()
        if metrics.get("rewritten", 0) or metrics.get("deleted", 0)
    ]
    return {
        "merged_student_document": merged,
        "deleted_student_ids": losing_ids,
        "rewrite_counts": rewrite_counts,
        "warnings": preview.get("warnings", []),
        "audit_payload": {
            "reason": reason,
            "primary_student_id": normalized_primary_id,
            "deleted_student_ids": losing_ids,
            "resolved_profile": normalized_profile,
            "rewrite_counts": rewrite_counts,
            "case_id": preview.get("case_id"),
        },
    }
