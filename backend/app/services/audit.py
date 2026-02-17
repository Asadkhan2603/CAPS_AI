from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from app.core.database import db


async def log_audit_event(
    *,
    actor_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None = None,
    detail: str | None = None,
) -> Dict[str, Any]:
    document = {
        "actor_user_id": actor_user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "detail": detail,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.audit_logs.insert_one(document)
    created = await db.audit_logs.find_one({"_id": result.inserted_id})
    return created or document
