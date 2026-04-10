from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.course_offering_read_models import sync_course_offering_read_models_for_ids


async def _enrich_class_slots(database: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return []
    offering_ids = [str(item.get("course_offering_id")) for item in items if item.get("course_offering_id")]
    if offering_ids:
        await sync_course_offering_read_models_for_ids(offering_ids=offering_ids, database=database)
    course_offering_read_models = getattr(database, "course_offering_read_models", None)
    if course_offering_read_models is None:
        offering_rows = []
    else:
        offering_rows = await course_offering_read_models.find(
        {"_id": {"$in": [parse_object_id(item) for item in offering_ids]}}
        ).to_list(length=len(offering_ids))
    offering_map = {str(item.get("_id")): item for item in offering_rows if item.get("_id")}

    enriched: list[dict[str, Any]] = []
    for item in items:
        offering = offering_map.get(str(item.get("course_offering_id") or ""))
        enriched.append(
            {
                **item,
                "subject_id": item.get("subject_id") or (offering or {}).get("subject_id"),
                "subject_name": item.get("subject_name") or (offering or {}).get("subject_name"),
                "subject_code": item.get("subject_code") or (offering or {}).get("subject_code"),
                "teacher_user_id": item.get("teacher_user_id") or (offering or {}).get("teacher_user_id"),
                "teacher_name": item.get("teacher_name") or (offering or {}).get("teacher_name"),
                "batch_id": item.get("batch_id") or (offering or {}).get("batch_id"),
                "batch_name": item.get("batch_name") or (offering or {}).get("batch_name"),
                "semester_id": item.get("semester_id") or (offering or {}).get("semester_id"),
                "semester_label": item.get("semester_label") or (offering or {}).get("semester_label"),
                "section_id": item.get("section_id") or (offering or {}).get("section_id"),
                "section_name": item.get("section_name") or (offering or {}).get("section_name"),
                "group_id": item.get("group_id") if item.get("group_id") is not None else (offering or {}).get("group_id"),
                "group_name": item.get("group_name") or (offering or {}).get("group_name"),
                "academic_year": item.get("academic_year") or (offering or {}).get("academic_year"),
                "offering_type": item.get("offering_type") or (offering or {}).get("offering_type"),
            }
        )
    return enriched


def _read_model_document_from_slot(slot: dict[str, Any]) -> dict[str, Any]:
    return {
        **slot,
        "_id": slot["_id"],
        "class_slot_id": str(slot["_id"]),
        "read_model_updated_at": datetime.now(timezone.utc),
    }


async def sync_class_slot_read_model(
    *,
    slot: dict[str, Any] | None = None,
    slot_id: str | None = None,
    database: Any = db,
) -> dict[str, Any] | None:
    class_slot_read_models = getattr(database, "class_slot_read_models", None)
    if class_slot_read_models is None:
        return slot
    if slot is None:
        if not slot_id:
            return None
        slot = await database.class_slots.find_one({"_id": parse_object_id(slot_id)})
    if not slot or not slot.get("_id"):
        if slot_id:
            await class_slot_read_models.delete_one({"_id": parse_object_id(slot_id)})
        return None

    enriched = await _enrich_class_slots(database, [slot])
    if not enriched:
        return None
    read_model = _read_model_document_from_slot(enriched[0])
    await class_slot_read_models.update_one(
        {"_id": read_model["_id"]},
        {"$set": read_model},
        upsert=True,
    )
    return read_model


async def sync_class_slot_read_models_for_ids(
    *,
    slot_ids: list[str],
    database: Any = db,
) -> dict[str, dict[str, Any]]:
    class_slot_read_models = getattr(database, "class_slot_read_models", None)
    if class_slot_read_models is None:
        return {}
    normalized_ids = [str(item) for item in slot_ids if item]
    if not normalized_ids:
        return {}

    object_ids = [parse_object_id(item) for item in normalized_ids]
    slots = await database.class_slots.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    found_ids = {str(item.get("_id")) for item in slots if item.get("_id")}
    missing_ids = [item for item in normalized_ids if item not in found_ids]
    if missing_ids:
        await class_slot_read_models.delete_many({"_id": {"$in": [parse_object_id(item) for item in missing_ids]}})

    if not slots:
        return {}

    enriched_slots = await _enrich_class_slots(database, slots)
    synced: dict[str, dict[str, Any]] = {}
    for item in enriched_slots:
        if not item.get("_id"):
            continue
        read_model = _read_model_document_from_slot(item)
        await class_slot_read_models.update_one(
            {"_id": read_model["_id"]},
            {"$set": read_model},
            upsert=True,
        )
        synced[str(read_model["_id"])] = read_model
    return synced


async def sync_class_slot_read_models_for_query(
    *,
    query: dict[str, Any],
    database: Any = db,
    limit: int = 5000,
) -> int:
    slots = await database.class_slots.find(query).to_list(length=max(1, limit))
    slot_ids = [str(item.get("_id")) for item in slots if item.get("_id")]
    await sync_class_slot_read_models_for_ids(slot_ids=slot_ids, database=database)
    return len(slot_ids)


async def sync_class_slot_read_models_for_offering_query(
    *,
    offering_query: dict[str, Any],
    database: Any = db,
    limit: int = 5000,
) -> int:
    offerings = await database.course_offerings.find(offering_query, {"_id": 1}).to_list(length=max(1, limit))
    offering_ids = [str(item.get("_id")) for item in offerings if item.get("_id")]
    if not offering_ids:
        return 0
    return await sync_class_slot_read_models_for_query(
        query={"course_offering_id": {"$in": offering_ids}},
        database=database,
        limit=limit,
    )
