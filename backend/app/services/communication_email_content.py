from __future__ import annotations

from datetime import datetime
from typing import Any


def build_notice_email_subject(notice: dict[str, Any]) -> str:
    return str(notice.get("title") or "Announcement").strip()


def build_notice_email_body(notice: dict[str, Any]) -> str:
    scope = str(notice.get("scope") or "college").replace("_", " ").strip().title()
    title = build_notice_email_subject(notice)
    message = str(notice.get("message") or "").strip()
    return f"{title}\n\n{message}\n\nAudience: {scope}\n\nThis announcement was sent from CAPS AI."


def build_notification_email_body(*, title: str, message: str, scope: str) -> str:
    normalized_scope = str(scope or "general").replace("_", " ").strip().title()
    return f"{title.strip()}\n\n{message.strip()}\n\nScope: {normalized_scope}\n\nThis message was sent from CAPS AI."


def build_notification_digest_email(*, digest_frequency: str, items: list[dict[str, Any]], generated_at: datetime) -> tuple[str, str]:
    frequency_label = "Daily" if digest_frequency == "daily_digest" else "Weekly"
    lines = [f"{frequency_label} CAPS AI Notification Digest", "", f"Generated: {generated_at.isoformat()}", ""]
    for index, item in enumerate(items, start=1):
        title = str(item.get("source_title") or item.get("title") or "Notification").strip()
        message = str(item.get("source_message") or item.get("message") or "").strip()
        scope = str(item.get("scope") or "global").replace("_", " ").strip().title()
        public_id = str(item.get("source_public_id") or "").strip()
        lines.append(f"{index}. {title}")
        if public_id:
            lines.append(f"   Ref: {public_id}")
        lines.append(f"   Scope: {scope}")
        if message:
            lines.append(f"   Message: {message}")
        lines.append("")
    subject = f"{frequency_label} CAPS AI Notification Digest ({len(items)})"
    lines.append("This digest was sent from CAPS AI.")
    return subject, "\n".join(lines)
