from __future__ import annotations

from typing import Any

from app.services.communication_deliveries import get_delivery_rows, upsert_email_deliveries
from app.services.communication_email_content import (
    build_notice_email_body,
    build_notice_email_subject,
    build_notification_email_body,
)
from app.services.communication_preferences import partition_email_recipients_by_preference
from app.services.outbound_email import send_outbound_email_batch


def _retryable_statuses(*, include_skipped: bool) -> set[str]:
    statuses = {"failed"}
    if include_skipped:
        statuses.add("skipped")
    return statuses


def _matches_retry_target(
    row: dict[str, Any],
    *,
    target_user_ids: set[str],
    target_emails: set[str],
) -> bool:
    if not target_user_ids and not target_emails:
        return True
    row_user_id = str(row.get("target_user_id") or "").strip()
    row_email = str(row.get("target_email") or "").strip().lower()
    return (row_user_id and row_user_id in target_user_ids) or (row_email and row_email in target_emails)


def _dedupe_recipients(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    recipients: list[dict[str, Any]] = []
    seen: set[tuple[str | None, str | None]] = set()
    for row in rows:
        user_id = str(row.get("target_user_id") or "").strip() or None
        email = str(row.get("target_email") or "").strip().lower() or None
        key = (user_id, email)
        if key in seen:
            continue
        seen.add(key)
        recipients.append(
            {
                "user_id": user_id,
                "email": email,
                "full_name": row.get("target_user_name"),
            }
        )
    return recipients


def _notice_disabled_reason(source_doc: dict[str, Any]) -> str:
    return "Recipient disabled club announcement email" if source_doc.get("scope") == "club" else "Recipient disabled announcement email"


async def retry_source_email_delivery(
    *,
    source_kind: str,
    source_doc: dict[str, Any],
    target_user_ids: list[str] | None = None,
    target_emails: list[str] | None = None,
    include_skipped: bool = True,
) -> int:
    source_id = str(source_doc.get("_id") or "").strip()
    if not source_id:
        return 0

    rows = await get_delivery_rows(source_kind=source_kind, source_id=source_id)
    retryable_rows = [
        row
        for row in rows
        if str(row.get("channel") or "").strip().lower() == "email"
        and str(row.get("status") or "").strip().lower() in _retryable_statuses(include_skipped=include_skipped)
        and _matches_retry_target(
            row,
            target_user_ids={str(value) for value in (target_user_ids or []) if value},
            target_emails={str(value).strip().lower() for value in (target_emails or []) if value},
        )
    ]
    recipients = _dedupe_recipients(retryable_rows)
    if not recipients:
        return 0

    if source_kind == "notice":
        preference_key = "club_announcement_email" if source_doc.get("scope") == "club" else "announcement_email"
        disabled_reason = _notice_disabled_reason(source_doc)
        subject = build_notice_email_subject(source_doc)
        body = build_notice_email_body(source_doc)
        metadata = {"scope": source_doc.get("scope"), "priority": source_doc.get("priority")}
    elif source_kind == "notification":
        preference_key = "notification_email"
        disabled_reason = "Recipient disabled notification email"
        subject = str(source_doc.get("title") or "Notification").strip()
        body = build_notification_email_body(
            title=str(source_doc.get("title") or ""),
            message=str(source_doc.get("message") or ""),
            scope=str(source_doc.get("scope") or "global"),
        )
        metadata = {"scope": source_doc.get("scope"), "priority": source_doc.get("priority")}
    else:
        return 0

    allowed_recipients, preference_skips = await partition_email_recipients_by_preference(
        recipients=recipients,
        preference_key=preference_key,
        disabled_reason=disabled_reason,
    )
    email_results = list(preference_skips)
    if allowed_recipients:
        email_results.extend(
            await send_outbound_email_batch(
                subject=subject,
                body=body,
                recipients=allowed_recipients,
            )
        )

    await upsert_email_deliveries(
        source_kind=source_kind,
        source_id=source_id,
        source_public_id=source_doc.get("public_id"),
        recipients=recipients,
        results=email_results,
        metadata=metadata,
    )
    return len(recipients)
