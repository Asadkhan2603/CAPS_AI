from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
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

    immutable_collection = getattr(db, "audit_logs_immutable", None)
    if immutable_collection is not None:
        try:
            previous = await immutable_collection.find_one(sort=[("created_at", -1)])
            previous_hash = (previous or {}).get("integrity_hash", "")
            canonical_payload = json.dumps(
                {
                    "actor_user_id": actor_user_id,
                    "action": action,
                    "action_type": action_type or action,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "detail": detail,
                    "severity": severity,
                    "created_at": document["created_at"].isoformat(),
                    "previous_hash": previous_hash,
                },
                sort_keys=True,
                default=str,
            )
            integrity_hash = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
            immutable_document = {
                **document,
                "integrity_hash": integrity_hash,
                "previous_hash": previous_hash,
                "source_audit_log_id": str(result.inserted_id),
            }
            await immutable_collection.insert_one(immutable_document)
        except Exception:
            pass

    return created or document
