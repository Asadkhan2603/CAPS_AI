from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from bson import ObjectId

from app.core.database import db
from app.core.schema_versions import COMMUNICATION_DELIVERY_SCHEMA_VERSION
from app.models.communication_deliveries import build_delivery_summary, empty_delivery_summary


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_email(value: Any) -> str | None:
    email = str(value or "").strip().lower()
    return email or None


def _recipient_query_key(*, target_user_id: str | None, target_email: str | None) -> dict[str, Any]:
    query = {
        "target_user_id": target_user_id,
        "target_email": target_email,
    }
    return query


async def _upsert_delivery_row(
    *,
    source_kind: str,
    source_id: str,
    source_public_id: str | None,
    channel: str,
    target_user_id: str | None,
    target_email: str | None,
    target_user_name: str | None,
    status: str,
    sent_at: datetime | None = None,
    read_at: datetime | None = None,
    error: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    query = {
        "source_kind": source_kind,
        "source_id": source_id,
        "channel": channel,
        **_recipient_query_key(target_user_id=target_user_id, target_email=target_email),
    }
    existing = await db.communication_deliveries.find_one(query)
    now = _utcnow()
    normalized_status = str(status or "pending").strip().lower() or "pending"
    existing_read_at = existing.get("read_at") if existing else None
    existing_sent_at = existing.get("sent_at") if existing else None
    if existing_read_at and normalized_status in {"sent", "read"}:
        normalized_status = "read"
        read_at = existing_read_at
    payload = {
        "source_kind": source_kind,
        "source_id": source_id,
        "source_public_id": source_public_id,
        "channel": channel,
        "target_user_id": target_user_id,
        "target_email": target_email,
        "target_user_name": target_user_name,
        "status": normalized_status,
        "sent_at": sent_at or existing_sent_at or (now if normalized_status in {"sent", "read"} else None),
        "read_at": read_at or existing_read_at,
        "error": error,
        "updated_at": now,
        "schema_version": COMMUNICATION_DELIVERY_SCHEMA_VERSION,
    }
    if metadata:
        payload["metadata"] = metadata
    if existing is None:
        payload["created_at"] = now
    else:
        payload["created_at"] = existing.get("created_at") or now
    await db.communication_deliveries.update_one(query, {"$set": payload}, upsert=True)


async def resolve_user_recipients(user_ids: Iterable[str]) -> list[dict[str, Any]]:
    normalized_ids = [str(user_id) for user_id in user_ids if user_id]
    if not normalized_ids:
        return []

    object_ids = [ObjectId(user_id) for user_id in normalized_ids if ObjectId.is_valid(user_id)]
    rows = []
    if object_ids:
        rows = await db.users.find({"_id": {"$in": object_ids}}).to_list(length=max(len(object_ids), 1))

    recipients = []
    seen: set[str] = set()
    for row in rows:
        user_id = str(row.get("_id") or "").strip()
        if not user_id or user_id in seen or row.get("is_active") is False:
            continue
        seen.add(user_id)
        recipients.append(
            {
                "user_id": user_id,
                "email": _normalize_email(row.get("email")),
                "full_name": str(row.get("full_name") or "").strip() or None,
            }
        )

    missing = [user_id for user_id in normalized_ids if user_id not in seen]
    for user_id in missing:
        recipients.append({"user_id": user_id, "email": None, "full_name": None})
    return recipients


async def resolve_all_active_user_recipients() -> list[dict[str, Any]]:
    rows = await db.users.find({"is_active": True}).to_list(length=100000)
    recipients = []
    for row in rows:
        user_id = str(row.get("_id") or "").strip()
        if not user_id:
            continue
        recipients.append(
            {
                "user_id": user_id,
                "email": _normalize_email(row.get("email")),
                "full_name": str(row.get("full_name") or "").strip() or None,
            }
        )
    return recipients


async def upsert_in_app_deliveries(
    *,
    source_kind: str,
    source_id: str,
    source_public_id: str | None,
    recipients: Iterable[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> int:
    inserted = 0
    seen: set[tuple[str | None, str | None]] = set()
    for recipient in recipients:
        target_user_id = str(recipient.get("user_id") or "").strip() or None
        target_email = _normalize_email(recipient.get("email"))
        dedupe_key = (target_user_id, target_email)
        if dedupe_key in seen:
            continue
        seen.add(dedupe_key)
        await _upsert_delivery_row(
            source_kind=source_kind,
            source_id=source_id,
            source_public_id=source_public_id,
            channel="in_app",
            target_user_id=target_user_id,
            target_email=target_email,
            target_user_name=recipient.get("full_name"),
            status="sent",
            metadata=metadata,
        )
        inserted += 1
    return inserted


async def upsert_email_deliveries(
    *,
    source_kind: str,
    source_id: str,
    source_public_id: str | None,
    recipients: Iterable[dict[str, Any]],
    results: Iterable[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> int:
    return await upsert_channel_deliveries(
        source_kind=source_kind,
        source_id=source_id,
        source_public_id=source_public_id,
        channel="email",
        recipients=recipients,
        results=results,
        metadata=metadata,
    )


async def upsert_channel_deliveries(
    *,
    source_kind: str,
    source_id: str,
    source_public_id: str | None,
    channel: str,
    recipients: Iterable[dict[str, Any]],
    results: Iterable[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> int:
    recipient_map = {
        (str(recipient.get("user_id") or "").strip() or None, _normalize_email(recipient.get("email"))): recipient
        for recipient in recipients
    }
    updated = 0
    for result in results:
        target_user_id = str(result.get("user_id") or "").strip() or None
        target_email = _normalize_email(result.get("email"))
        recipient = recipient_map.get((target_user_id, target_email), {})
        await _upsert_delivery_row(
            source_kind=source_kind,
            source_id=source_id,
            source_public_id=source_public_id,
            channel=channel,
            target_user_id=target_user_id,
            target_email=target_email,
            target_user_name=recipient.get("full_name"),
            status=str(result.get("status") or "pending"),
            sent_at=result.get("sent_at"),
            error=str(result.get("error") or "")[:500] or None,
            metadata={
                **(metadata or {}),
                **(result.get("metadata") or {}),
            }
            if metadata or result.get("metadata")
            else None,
        )
        updated += 1
    return updated


async def upsert_in_app_delivery_results(
    *,
    source_kind: str,
    source_id: str,
    source_public_id: str | None,
    recipients: Iterable[dict[str, Any]],
    results: Iterable[dict[str, Any]],
    metadata: dict[str, Any] | None = None,
) -> int:
    return await upsert_channel_deliveries(
        source_kind=source_kind,
        source_id=source_id,
        source_public_id=source_public_id,
        channel="in_app",
        recipients=recipients,
        results=results,
        metadata=metadata,
    )


async def mark_delivery_read(*, source_kind: str, source_id: str, target_user_id: str) -> dict[str, Any] | None:
    query = {
        "source_kind": source_kind,
        "source_id": source_id,
        "channel": "in_app",
        "target_user_id": target_user_id,
    }
    existing = await db.communication_deliveries.find_one(query)
    now = _utcnow()
    await db.communication_deliveries.update_one(
        query,
        {
            "$set": {
                "source_kind": source_kind,
                "source_id": source_id,
                "channel": "in_app",
                "target_user_id": target_user_id,
                "status": "read",
                "sent_at": (existing or {}).get("sent_at") or now,
                "read_at": now,
                "updated_at": now,
                "created_at": (existing or {}).get("created_at") or now,
                "schema_version": COMMUNICATION_DELIVERY_SCHEMA_VERSION,
            }
        },
        upsert=True,
    )
    return await db.communication_deliveries.find_one(query)


async def get_delivery_summaries(*, source_kind: str, source_ids: Iterable[str]) -> dict[str, dict[str, Any]]:
    normalized_ids = [str(source_id) for source_id in source_ids if source_id]
    if not normalized_ids:
        return {}
    rows = await db.communication_deliveries.find(
        {
            "source_kind": source_kind,
            "source_id": {"$in": normalized_ids},
        }
    ).to_list(length=100000)

    grouped: dict[str, list[dict[str, Any]]] = {source_id: [] for source_id in normalized_ids}
    for row in rows:
        source_id = str(row.get("source_id") or "")
        if source_id in grouped:
            grouped[source_id].append(row)
    return {source_id: build_delivery_summary(grouped.get(source_id, [])) for source_id in normalized_ids}


async def get_delivery_rows(*, source_kind: str, source_id: str) -> list[dict[str, Any]]:
    if not source_id:
        return []
    rows = await db.communication_deliveries.find(
        {
            "source_kind": source_kind,
            "source_id": str(source_id),
        }
    ).to_list(length=100000)
    return list(rows)


async def get_delivery_read_map(*, source_kind: str, source_ids: Iterable[str], target_user_id: str) -> dict[str, bool]:
    normalized_ids = [str(source_id) for source_id in source_ids if source_id]
    if not normalized_ids or not target_user_id:
        return {}
    rows = await db.communication_deliveries.find(
        {
            "source_kind": source_kind,
            "source_id": {"$in": normalized_ids},
            "channel": "in_app",
            "target_user_id": target_user_id,
        }
    ).to_list(length=max(len(normalized_ids), 1))
    return {
        str(row.get("source_id")): bool(row.get("read_at") or str(row.get("status") or "").strip().lower() == "read")
        for row in rows
        if row.get("source_id")
    }


def default_delivery_summary() -> dict[str, Any]:
    return empty_delivery_summary()
