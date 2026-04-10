from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.academic_enrichment import enrich_batch_documents


def _normalize_batch_id(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def _collection(database: Any, name: str):
    return getattr(database, name, None)


def _read_model_document_from_batch(batch: dict[str, Any]) -> dict[str, Any]:
    return {
        **batch,
        "_id": batch["_id"],
        "batch_id": str(batch["_id"]),
        "read_model_updated_at": datetime.now(timezone.utc),
    }


async def sync_batch_read_model(
    *,
    batch: dict[str, Any] | None = None,
    batch_id: str | None = None,
    database: Any = db,
) -> dict[str, Any] | None:
    batch_read_models = _collection(database, "batch_read_models")
    if batch_read_models is None:
        return batch
    if batch is None:
        if not batch_id:
            return None
        batch = await database.batches.find_one({"_id": parse_object_id(batch_id)})
    if not batch or not batch.get("_id"):
        if batch_id:
            await batch_read_models.delete_one({"_id": parse_object_id(batch_id)})
        return None

    enriched = await enrich_batch_documents(database, [batch])
    if not enriched:
        return None
    read_model = _read_model_document_from_batch(enriched[0])
    await batch_read_models.update_one(
        {"_id": read_model["_id"]},
        {"$set": read_model},
        upsert=True,
    )
    return read_model


async def sync_batch_read_models_for_ids(
    *,
    batch_ids: list[str],
    database: Any = db,
) -> dict[str, dict[str, Any]]:
    batch_read_models = _collection(database, "batch_read_models")
    if batch_read_models is None:
        return {}
    normalized_ids = [_normalize_batch_id(item) for item in batch_ids]
    normalized_ids = [item for item in normalized_ids if item]
    if not normalized_ids:
        return {}

    object_ids = [parse_object_id(item) for item in normalized_ids]
    batches = await database.batches.find({"_id": {"$in": object_ids}}).to_list(length=len(object_ids))
    found_ids = {str(item.get("_id")) for item in batches if item.get("_id")}
    missing_ids = [item for item in normalized_ids if item not in found_ids]
    if missing_ids:
        await batch_read_models.delete_many({"_id": {"$in": [parse_object_id(item) for item in missing_ids]}})

    if not batches:
        return {}

    enriched_batches = await enrich_batch_documents(database, batches)
    synced: dict[str, dict[str, Any]] = {}
    for item in enriched_batches:
        if not item.get("_id"):
            continue
        read_model = _read_model_document_from_batch(item)
        await batch_read_models.update_one(
            {"_id": read_model["_id"]},
            {"$set": read_model},
            upsert=True,
        )
        synced[str(read_model["_id"])] = read_model
    return synced


async def sync_batch_read_models_for_query(
    *,
    query: dict[str, Any],
    database: Any = db,
    limit: int = 5000,
) -> int:
    batches = await database.batches.find(query).to_list(length=max(1, limit))
    batch_ids = [str(item.get("_id")) for item in batches if item.get("_id")]
    await sync_batch_read_models_for_ids(batch_ids=batch_ids, database=database)
    return len(batch_ids)


async def get_batch_read_model(
    *,
    batch_id: str,
    database: Any = db,
) -> dict[str, Any] | None:
    batch_read_models = _collection(database, "batch_read_models")
    if batch_read_models is None:
        return await database.batches.find_one({"_id": parse_object_id(batch_id)})
    read_model = await batch_read_models.find_one({"_id": parse_object_id(batch_id)})
    if read_model:
        return read_model
    return await sync_batch_read_model(batch_id=batch_id, database=database)


async def hydrate_batches_from_read_models(
    *,
    source_batches: list[dict[str, Any]],
    database: Any = db,
) -> list[dict[str, Any]]:
    if not source_batches:
        return []
    batch_read_models = _collection(database, "batch_read_models")
    if batch_read_models is None:
        return source_batches

    batch_ids = [str(item.get("_id")) for item in source_batches if item.get("_id")]
    read_models = await batch_read_models.find(
        {"_id": {"$in": [parse_object_id(item) for item in batch_ids]}}
    ).to_list(length=len(batch_ids))
    read_model_map = {str(item.get("_id")): item for item in read_models if item.get("_id")}

    missing_ids = [item_id for item_id in batch_ids if item_id not in read_model_map]
    if missing_ids:
        synced = await sync_batch_read_models_for_ids(batch_ids=missing_ids, database=database)
        read_model_map.update(synced)

    hydrated: list[dict[str, Any]] = []
    for batch in source_batches:
        batch_id = str(batch.get("_id"))
        hydrated.append(read_model_map.get(batch_id) or batch)
    return hydrated
