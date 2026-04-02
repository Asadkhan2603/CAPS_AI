from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.academic_enrichment import enrich_section_documents


def _normalize_section_id(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _read_model_document_from_section(section: dict[str, Any]) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    return {
        **section,
        "_id": section["_id"],
        "section_id": str(section["_id"]),
        "read_model_updated_at": now,
    }


async def sync_section_read_model(
    *,
    section: dict[str, Any] | None = None,
    section_id: str | None = None,
    database: Any = db,
) -> dict[str, Any] | None:
    if section is None:
        if not section_id:
            return None
        section = await database.classes.find_one({"_id": parse_object_id(section_id)})
    if not section or not section.get("_id"):
        if section_id:
            await database.section_read_models.delete_one({"_id": parse_object_id(section_id)})
        return None

    enriched = await enrich_section_documents(database, [section])
    if not enriched:
        return None
    read_model = _read_model_document_from_section(enriched[0])
    await database.section_read_models.update_one(
        {"_id": read_model["_id"]},
        {"$set": read_model},
        upsert=True,
    )
    return read_model


async def sync_section_read_models_for_ids(
    *,
    section_ids: list[str],
    database: Any = db,
) -> dict[str, dict[str, Any]]:
    normalized_ids = [_normalize_section_id(item) for item in section_ids]
    normalized_ids = [item for item in normalized_ids if item]
    if not normalized_ids:
        return {}

    object_ids = [parse_object_id(item) for item in normalized_ids]
    sections = await database.classes.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    found_ids = {str(item.get("_id")) for item in sections if item.get("_id")}
    missing_ids = [item for item in normalized_ids if item not in found_ids]
    if missing_ids:
        await database.section_read_models.delete_many({"_id": {"$in": [parse_object_id(item) for item in missing_ids]}})

    if not sections:
        return {}

    enriched_sections = await enrich_section_documents(database, sections)
    synced: dict[str, dict[str, Any]] = {}
    for item in enriched_sections:
        if not item.get("_id"):
            continue
        read_model = _read_model_document_from_section(item)
        await database.section_read_models.update_one(
            {"_id": read_model["_id"]},
            {"$set": read_model},
            upsert=True,
        )
        synced[str(read_model["_id"])] = read_model
    return synced


async def sync_section_read_models_for_query(
    *,
    query: dict[str, Any],
    database: Any = db,
    limit: int = 5000,
) -> int:
    sections = await database.classes.find(query).to_list(length=max(1, limit))
    section_ids = [str(item.get("_id")) for item in sections if item.get("_id")]
    await sync_section_read_models_for_ids(section_ids=section_ids, database=database)
    return len(section_ids)


async def get_section_read_model(
    *,
    section_id: str,
    database: Any = db,
) -> dict[str, Any] | None:
    read_model = await database.section_read_models.find_one({"_id": parse_object_id(section_id)})
    if read_model:
        return read_model
    return await sync_section_read_model(section_id=section_id, database=database)


async def hydrate_sections_from_read_models(
    *,
    source_sections: list[dict[str, Any]],
    database: Any = db,
) -> list[dict[str, Any]]:
    if not source_sections:
        return []

    section_ids = [str(item.get("_id")) for item in source_sections if item.get("_id")]
    read_models = await database.section_read_models.find(
        {"_id": {"$in": [parse_object_id(item) for item in section_ids]}}
    ).to_list(length=len(section_ids))
    read_model_map = {str(item.get("_id")): item for item in read_models if item.get("_id")}

    missing_ids = [item_id for item_id in section_ids if item_id not in read_model_map]
    if missing_ids:
        synced = await sync_section_read_models_for_ids(section_ids=missing_ids, database=database)
        read_model_map.update(synced)

    hydrated: list[dict[str, Any]] = []
    for section in source_sections:
        section_id = str(section.get("_id"))
        hydrated.append(read_model_map.get(section_id) or section)
    return hydrated
