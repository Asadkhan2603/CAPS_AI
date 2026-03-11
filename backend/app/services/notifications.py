from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from app.core.database import db


async def create_notification(
    *,
    title: str,
    message: str,
    priority: str = "normal",
    scope: str = "global",
    target_user_id: str | None = None,
    created_by: str | None = None,
) -> Dict[str, Any]:
    document = {
        "title": title.strip(),
        "message": message.strip(),
        "priority": priority,
        "scope": scope,
        "target_user_id": target_user_id,
        "created_by": created_by,
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.notifications.insert_one(document)
    created = await db.notifications.find_one({"_id": result.inserted_id})
    return created or document


async def create_notifications_bulk(
    *,
    title: str,
    message: str,
    priority: str = "normal",
    scope: str = "global",
    target_user_ids: Iterable[str],
    created_by: str | None = None,
    batch_size: int = 1000,
) -> int:
    normalized_title = title.strip()
    normalized_message = message.strip()
    pending: list[dict[str, Any]] = []
    inserted = 0
    safe_batch_size = max(100, min(batch_size, 5000))

    for target_user_id in target_user_ids:
        if not target_user_id:
            continue
        pending.append(
            {
                "title": normalized_title,
                "message": normalized_message,
                "priority": priority,
                "scope": scope,
                "target_user_id": target_user_id,
                "created_by": created_by,
                "is_read": False,
                "created_at": datetime.now(timezone.utc),
            }
        )
        if len(pending) >= safe_batch_size:
            result = await db.notifications.insert_many(pending, ordered=False)
            inserted += len(result.inserted_ids)
            pending = []

    if pending:
        result = await db.notifications.insert_many(pending, ordered=False)
        inserted += len(result.inserted_ids)
    return inserted
