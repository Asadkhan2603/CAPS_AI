from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db
from app.core.mongo import parse_object_id


async def _related_lookup_map(database: Any, collection_name: str, ids: list[str]) -> dict[str, dict[str, Any]]:
    if not ids:
        return {}
    collection = getattr(database, collection_name, None)
    if collection is None:
        return {}
    object_ids = [parse_object_id(item_id) for item_id in ids if item_id]
    if not object_ids:
        return {}
    rows = await collection.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    return {str(row.get("_id")): row for row in rows if row.get("_id")}


async def _enrich_course_offerings(database: Any, items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not items:
        return []
    subject_map = await _related_lookup_map(database, "subjects", list({str(item.get("subject_id")) for item in items if item.get("subject_id")}))
    teacher_map = await _related_lookup_map(database, "users", list({str(item.get("teacher_user_id")) for item in items if item.get("teacher_user_id")}))
    batch_map = await _related_lookup_map(database, "batches", list({str(item.get("batch_id")) for item in items if item.get("batch_id")}))
    section_map = await _related_lookup_map(database, "classes", list({str(item.get("section_id")) for item in items if item.get("section_id")}))
    group_map = await _related_lookup_map(database, "groups", list({str(item.get("group_id")) for item in items if item.get("group_id")}))
    semester_map = await _related_lookup_map(database, "semesters", list({str(item.get("semester_id")) for item in items if item.get("semester_id")}))

    enriched: list[dict[str, Any]] = []
    for item in items:
        subject = subject_map.get(str(item.get("subject_id") or ""))
        teacher = teacher_map.get(str(item.get("teacher_user_id") or ""))
        batch = batch_map.get(str(item.get("batch_id") or ""))
        section = section_map.get(str(item.get("section_id") or ""))
        group = group_map.get(str(item.get("group_id") or ""))
        semester = semester_map.get(str(item.get("semester_id") or ""))
        enriched.append(
            {
                **item,
                "subject_name": item.get("subject_name") or (subject or {}).get("name"),
                "subject_code": item.get("subject_code") or (subject or {}).get("code"),
                "teacher_name": item.get("teacher_name") or (teacher or {}).get("full_name"),
                "batch_name": item.get("batch_name") or (batch or {}).get("name"),
                "section_name": item.get("section_name") or (section or {}).get("name"),
                "group_name": item.get("group_name") or (group or {}).get("name"),
                "semester_label": item.get("semester_label") or (semester or {}).get("label"),
            }
        )
    return enriched


def _read_model_document_from_offering(offering: dict[str, Any]) -> dict[str, Any]:
    return {
        **offering,
        "_id": offering["_id"],
        "course_offering_id": str(offering["_id"]),
        "read_model_updated_at": datetime.now(timezone.utc),
    }


async def sync_course_offering_read_model(
    *,
    offering: dict[str, Any] | None = None,
    offering_id: str | None = None,
    database: Any = db,
) -> dict[str, Any] | None:
    course_offering_read_models = getattr(database, "course_offering_read_models", None)
    if course_offering_read_models is None:
        return offering
    if offering is None:
        if not offering_id:
            return None
        offering = await database.course_offerings.find_one({"_id": parse_object_id(offering_id)})
    if not offering or not offering.get("_id"):
        if offering_id:
            await course_offering_read_models.delete_one({"_id": parse_object_id(offering_id)})
        return None

    enriched = await _enrich_course_offerings(database, [offering])
    if not enriched:
        return None
    read_model = _read_model_document_from_offering(enriched[0])
    await course_offering_read_models.update_one(
        {"_id": read_model["_id"]},
        {"$set": read_model},
        upsert=True,
    )
    return read_model


async def sync_course_offering_read_models_for_ids(
    *,
    offering_ids: list[str],
    database: Any = db,
) -> dict[str, dict[str, Any]]:
    course_offering_read_models = getattr(database, "course_offering_read_models", None)
    if course_offering_read_models is None:
        return {}
    normalized_ids = [str(item) for item in offering_ids if item]
    if not normalized_ids:
        return {}

    object_ids = [parse_object_id(item) for item in normalized_ids]
    offerings = await database.course_offerings.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    found_ids = {str(item.get("_id")) for item in offerings if item.get("_id")}
    missing_ids = [item for item in normalized_ids if item not in found_ids]
    if missing_ids:
        await course_offering_read_models.delete_many({"_id": {"$in": [parse_object_id(item) for item in missing_ids]}})

    if not offerings:
        return {}

    enriched_offerings = await _enrich_course_offerings(database, offerings)
    synced: dict[str, dict[str, Any]] = {}
    for item in enriched_offerings:
        if not item.get("_id"):
            continue
        read_model = _read_model_document_from_offering(item)
        await course_offering_read_models.update_one(
            {"_id": read_model["_id"]},
            {"$set": read_model},
            upsert=True,
        )
        synced[str(read_model["_id"])] = read_model
    return synced


async def sync_course_offering_read_models_for_query(
    *,
    query: dict[str, Any],
    database: Any = db,
    limit: int = 5000,
) -> list[str]:
    offerings = await database.course_offerings.find(query).to_list(length=max(1, limit))
    offering_ids = [str(item.get("_id")) for item in offerings if item.get("_id")]
    await sync_course_offering_read_models_for_ids(offering_ids=offering_ids, database=database)
    return offering_ids


async def hydrate_course_offerings_from_read_models(
    *,
    source_offerings: list[dict[str, Any]],
    database: Any = db,
) -> list[dict[str, Any]]:
    if not source_offerings:
        return []
    course_offering_read_models = getattr(database, "course_offering_read_models", None)
    if course_offering_read_models is None:
        return source_offerings

    offering_ids = [str(item.get("_id")) for item in source_offerings if item.get("_id")]
    read_models = await course_offering_read_models.find(
        {"_id": {"$in": [parse_object_id(item) for item in offering_ids]}}
    ).to_list(length=len(offering_ids))
    read_model_map = {str(item.get("_id")): item for item in read_models if item.get("_id")}

    missing_ids = [item_id for item_id in offering_ids if item_id not in read_model_map]
    if missing_ids:
        synced = await sync_course_offering_read_models_for_ids(offering_ids=missing_ids, database=database)
        read_model_map.update(synced)

    hydrated: list[dict[str, Any]] = []
    for offering in source_offerings:
        offering_id = str(offering.get("_id"))
        hydrated.append(read_model_map.get(offering_id) or offering)
    return hydrated
