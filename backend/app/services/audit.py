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
    action_type: str | None = None,
    resource_type: str | None = None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    ip_address: str | None = None,
    user_agent: str | None = None,
    severity: str = "low",
) -> Dict[str, Any]:
    document = {
        "actor_user_id": actor_user_id,
        "action": action,
        "action_type": action_type or action,
        "entity_type": entity_type,
        "resource_type": resource_type or entity_type,
        "entity_id": entity_id,
        "detail": detail,
        "old_value": old_value,
        "new_value": new_value,
        "ip_address": ip_address,
        "user_agent": user_agent,
        "severity": severity,
        "created_at": datetime.now(timezone.utc),
    }
    result = await db.audit_logs.insert_one(document)
    created = await db.audit_logs.find_one({"_id": result.inserted_id})
    return created or document
