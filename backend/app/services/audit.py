from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict

from app.core.database import db
from app.core.schema_versions import AUDIT_LOG_SCHEMA_VERSION

logger = logging.getLogger(__name__)


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
    created_at = datetime.now(timezone.utc)
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
        "created_at": created_at,
        "schema_version": AUDIT_LOG_SCHEMA_VERSION,
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
                    "created_at": created_at.isoformat(),
                    "schema_version": AUDIT_LOG_SCHEMA_VERSION,
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


async def log_destructive_action_event(
    *,
    actor_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    stage: str,
    detail: str,
    review_id: str | None = None,
    governance_required: bool | None = None,
    governance_completed: bool | None = None,
    outcome: str | None = None,
    metadata: dict[str, Any] | None = None,
    severity: str = "medium",
) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "event": "destructive_action.telemetry",
        "actor_user_id": actor_user_id,
        "action": action,
        "entity_type": entity_type,
        "entity_id": entity_id,
        "stage": stage,
        "detail": detail,
        "review_id_supplied": bool(review_id),
        "review_id": review_id,
        "governance_required": governance_required,
        "governance_completed": governance_completed,
        "outcome": outcome or stage,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info(payload)
    try:
        return await log_audit_event(
            actor_user_id=actor_user_id,
            action=action,
            action_type="destructive_action.telemetry",
            entity_type=entity_type,
            entity_id=entity_id,
            detail=detail,
            new_value=payload,
            severity=severity,
        )
    except Exception:
        logger.exception(
            "Failed to persist destructive action telemetry",
            extra={"action": action, "entity_type": entity_type, "entity_id": entity_id, "stage": stage},
        )
        return payload
