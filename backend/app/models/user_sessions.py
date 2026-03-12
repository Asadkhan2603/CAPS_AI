from typing import Any, Dict

from app.core.schema_versions import USER_SESSION_SCHEMA_VERSION, normalize_schema_version


def user_session_public(document: Dict[str, Any], *, user: Dict[str, Any] | None = None) -> Dict[str, Any]:
    user = user or {}
    revoked_at = document.get("revoked_at")
    return {
        "id": str(document.get("_id")),
        "user_id": document.get("user_id"),
        "user_name": user.get("full_name"),
        "user_email": user.get("email"),
        "fingerprint": document.get("fingerprint"),
        "ip_address": document.get("ip_address") or document.get("last_seen_ip"),
        "last_seen_ip": document.get("last_seen_ip"),
        "user_agent": document.get("user_agent"),
        "created_at": document.get("created_at"),
        "last_seen_at": document.get("last_seen_at"),
        "rotated_at": document.get("rotated_at"),
        "revoked_at": revoked_at,
        "status": "revoked" if revoked_at else "active",
        "schema_version": normalize_schema_version(
            document.get("schema_version"),
            default=USER_SESSION_SCHEMA_VERSION,
        ),
    }
