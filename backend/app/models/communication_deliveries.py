from __future__ import annotations

from datetime import datetime
from typing import Any


def empty_delivery_summary() -> dict[str, Any]:
    return {
        "total_recipients": 0,
        "read_count": 0,
        "unread_count": 0,
        "in_app": {
            "total": 0,
            "sent_count": 0,
            "read_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "pending_count": 0,
            "last_sent_at": None,
            "last_read_at": None,
            "last_error": None,
        },
        "email": {
            "total": 0,
            "sent_count": 0,
            "read_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "pending_count": 0,
            "last_sent_at": None,
            "last_read_at": None,
            "last_error": None,
        },
    }


def _recipient_key(row: dict[str, Any]) -> str | None:
    target_user_id = str(row.get("target_user_id") or "").strip()
    if target_user_id:
        return f"user:{target_user_id}"
    target_email = str(row.get("target_email") or "").strip().lower()
    return f"email:{target_email}" if target_email else None


def _apply_channel_row(summary: dict[str, Any], row: dict[str, Any]) -> None:
    status = str(row.get("status") or "pending").strip().lower()
    sent_at = row.get("sent_at")
    read_at = row.get("read_at")
    error = str(row.get("error") or "").strip() or None

    summary["total"] += 1
    if status in {"sent", "read"}:
        summary["sent_count"] += 1
    elif status == "failed":
        summary["failed_count"] += 1
    elif status == "skipped":
        summary["skipped_count"] += 1
    else:
        summary["pending_count"] += 1

    if read_at or status == "read":
        summary["read_count"] += 1

    if isinstance(sent_at, datetime) and (summary["last_sent_at"] is None or sent_at > summary["last_sent_at"]):
        summary["last_sent_at"] = sent_at
    if isinstance(read_at, datetime) and (summary["last_read_at"] is None or read_at > summary["last_read_at"]):
        summary["last_read_at"] = read_at
    if error and not summary["last_error"]:
        summary["last_error"] = error


def build_delivery_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary = empty_delivery_summary()
    recipient_keys: set[str] = set()
    read_recipient_keys: set[str] = set()

    for row in rows:
        recipient_key = _recipient_key(row)
        if recipient_key:
            recipient_keys.add(recipient_key)

        channel = str(row.get("channel") or "").strip().lower()
        if channel == "email":
            _apply_channel_row(summary["email"], row)
            continue

        _apply_channel_row(summary["in_app"], row)
        if recipient_key and (row.get("read_at") or str(row.get("status") or "").strip().lower() == "read"):
            read_recipient_keys.add(recipient_key)

    if summary["in_app"]["total"] > 0:
        summary["total_recipients"] = len(recipient_keys) or summary["in_app"]["total"]
    else:
        summary["total_recipients"] = len(recipient_keys)
    summary["read_count"] = len(read_recipient_keys)
    summary["unread_count"] = max(summary["total_recipients"] - summary["read_count"], 0)
    return summary
