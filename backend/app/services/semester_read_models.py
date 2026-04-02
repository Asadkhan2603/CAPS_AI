from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.academic_enrichment import enrich_semester_documents


def _normalize_semester_id(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _read_model_document_from_semester(semester: dict[str, Any]) -> dict[str, Any]:
    return {
        **semester,
        "_id": semester["_id"],
        "semester_id": str(semester["_id"]),
        "read_model_updated_at": datetime.now(timezone.utc),
    }


async def sync_semester_read_model(
    *,
    semester: dict[str, Any] | None = None,
    semester_id: str | None = None,
    database: Any = db,
) -> dict[str, Any] | None:
    if semester is None:
        if not semester_id:
            return None
        semester = await database.semesters.find_one({"_id": parse_object_id(semester_id)})
    if not semester or not semester.get("_id"):
        if semester_id:
            await database.semester_read_models.delete_one({"_id": parse_object_id(semester_id)})
        return None

    enriched = await enrich_semester_documents(database, [semester])
    if not enriched:
        return None
    read_model = _read_model_document_from_semester(enriched[0])
    await database.semester_read_models.update_one(
        {"_id": read_model["_id"]},
        {"$set": read_model},
        upsert=True,
    )
    return read_model


async def sync_semester_read_models_for_ids(
    *,
    semester_ids: list[str],
    database: Any = db,
) -> dict[str, dict[str, Any]]:
    normalized_ids = [_normalize_semester_id(item) for item in semester_ids]
    normalized_ids = [item for item in normalized_ids if item]
    if not normalized_ids:
        return {}

    object_ids = [parse_object_id(item) for item in normalized_ids]
    semesters = await database.semesters.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    found_ids = {str(item.get("_id")) for item in semesters if item.get("_id")}
    missing_ids = [item for item in normalized_ids if item not in found_ids]
    if missing_ids:
        await database.semester_read_models.delete_many({"_id": {"$in": [parse_object_id(item) for item in missing_ids]}})

    if not semesters:
        return {}

    enriched_semesters = await enrich_semester_documents(database, semesters)
    synced: dict[str, dict[str, Any]] = {}
    for item in enriched_semesters:
        if not item.get("_id"):
            continue
        read_model = _read_model_document_from_semester(item)
        await database.semester_read_models.update_one(
            {"_id": read_model["_id"]},
            {"$set": read_model},
            upsert=True,
        )
        synced[str(read_model["_id"])] = read_model
    return synced


async def sync_semester_read_models_for_query(
    *,
    query: dict[str, Any],
    database: Any = db,
    limit: int = 5000,
) -> int:
    semesters = await database.semesters.find(query).to_list(length=max(1, limit))
    semester_ids = [str(item.get("_id")) for item in semesters if item.get("_id")]
    await sync_semester_read_models_for_ids(semester_ids=semester_ids, database=database)
    return len(semester_ids)


async def get_semester_read_model(
    *,
    semester_id: str,
    database: Any = db,
) -> dict[str, Any] | None:
    read_model = await database.semester_read_models.find_one({"_id": parse_object_id(semester_id)})
    if read_model:
        return read_model
    return await sync_semester_read_model(semester_id=semester_id, database=database)


async def hydrate_semesters_from_read_models(
    *,
    source_semesters: list[dict[str, Any]],
    database: Any = db,
) -> list[dict[str, Any]]:
    if not source_semesters:
        return []

    semester_ids = [str(item.get("_id")) for item in source_semesters if item.get("_id")]
    read_models = await database.semester_read_models.find(
        {"_id": {"$in": [parse_object_id(item) for item in semester_ids]}}
    ).to_list(length=len(semester_ids))
    read_model_map = {str(item.get("_id")): item for item in read_models if item.get("_id")}

    missing_ids = [item_id for item_id in semester_ids if item_id not in read_model_map]
    if missing_ids:
        synced = await sync_semester_read_models_for_ids(semester_ids=missing_ids, database=database)
        read_model_map.update(synced)

    hydrated: list[dict[str, Any]] = []
    for semester in source_semesters:
        semester_id = str(semester.get("_id"))
        hydrated.append(read_model_map.get(semester_id) or semester)
    return hydrated
