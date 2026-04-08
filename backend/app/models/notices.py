from typing import Any, Dict

from app.core.schema_versions import NOTICE_SCHEMA_VERSION, normalize_schema_version
from app.models.communication_deliveries import empty_delivery_summary


def notice_public(document: Dict[str, Any], *, current_user_id: str | None = None) -> Dict[str, Any]:
    seen_by = [str(item) for item in (document.get("seen_by", []) or []) if item]
    current_user_key = str(current_user_id) if current_user_id else None
    delivery_summary = document.get("delivery_summary") or empty_delivery_summary()
    delivery_read_count = int(delivery_summary.get("read_count", 0) or 0)
    return {
        "id": str(document["_id"]),
        "title": document.get("title", ""),
        "message": document.get("message", ""),
        "priority": document.get("priority", "normal"),
        "scope": document.get("scope", "college"),
        "scope_ref_id": document.get("scope_ref_id"),
        "expires_at": document.get("expires_at"),
        "images": document.get("images", []) or [],
        "is_pinned": document.get("is_pinned", False),
        "template_key": document.get("template_key"),
        "scheduled_at": document.get("scheduled_at"),
        "read_count": max(int(document.get("read_count", 0) or 0), delivery_read_count),
        "seen_by": seen_by,
        "is_read": bool(
            current_user_key
            and (
                current_user_key in seen_by
                or bool(document.get("current_user_delivery_read"))
            )
        ),
        "fanout_status": document.get("fanout_status", "queued"),
        "fanout_attempts": int(document.get("fanout_attempts", 0) or 0),
        "fanout_last_attempt_at": document.get("fanout_last_attempt_at"),
        "fanout_next_retry_at": document.get("fanout_next_retry_at"),
        "fanout_count": int(document.get("fanout_count", 0) or 0),
        "fanout_dispatched_at": document.get("fanout_dispatched_at"),
        "fanout_failed_at": document.get("fanout_failed_at"),
        "fanout_error": document.get("fanout_error"),
        "delivery_summary": delivery_summary,
        "created_by": document.get("created_by"),
        "is_active": document.get("is_active", True),
        "created_at": document.get("created_at"),
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=NOTICE_SCHEMA_VERSION,
        ),
    }
