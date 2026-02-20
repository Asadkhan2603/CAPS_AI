from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

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
