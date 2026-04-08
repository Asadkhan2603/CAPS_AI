from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.database import db
from app.core.schema_versions import COMMUNICATION_DIGEST_SCHEMA_VERSION
from app.services.communication_deliveries import upsert_email_deliveries
from app.services.communication_email_content import build_notification_digest_email
from app.services.outbound_email import send_outbound_email_batch


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _next_daily_digest_run(*, hour_utc: int, now: datetime) -> datetime:
    candidate = now.replace(hour=max(0, min(23, int(hour_utc))), minute=0, second=0, microsecond=0)
    if candidate <= now:
        candidate += timedelta(days=1)
    return candidate


def _next_weekly_digest_run(*, day_of_week: int, hour_utc: int, now: datetime) -> datetime:
    day = max(0, min(6, int(day_of_week)))
    candidate = now.replace(hour=max(0, min(23, int(hour_utc))), minute=0, second=0, microsecond=0)
    days_ahead = (day - candidate.weekday()) % 7
    if days_ahead == 0 and candidate <= now:
        days_ahead = 7
    return candidate + timedelta(days=days_ahead)


def _digest_scheduled_for(*, digest_frequency: str, digest_preferences: dict[str, Any] | None, now: datetime) -> datetime:
    preferences = digest_preferences or {}
    if digest_frequency == "weekly_digest":
        return _next_weekly_digest_run(
            day_of_week=int(preferences.get("weekly_digest_day_of_week", 0) or 0),
            hour_utc=int(preferences.get("daily_digest_hour_utc", 8) or 8),
            now=now,
        )
    return _next_daily_digest_run(hour_utc=int(preferences.get("daily_digest_hour_utc", 8) or 8), now=now)


async def queue_notification_digests(
    *,
    source_doc: dict[str, Any],
    recipients: list[dict[str, Any]],
    digest_frequency: str,
) -> list[dict[str, Any]]:
    source_id = str(source_doc.get("_id") or "").strip()
    if not source_id or not recipients:
        return []

    now = _utcnow()
    queued_results: list[dict[str, Any]] = []
    for recipient in recipients:
        target_user_id = str(recipient.get("user_id") or "").strip() or None
        target_email = str(recipient.get("email") or "").strip().lower() or None
        scheduled_for = _digest_scheduled_for(
            digest_frequency=digest_frequency,
            digest_preferences=recipient.get("digest_preferences") or {},
            now=now,
        )
        query = {
            "source_kind": "notification",
            "source_id": source_id,
            "target_user_id": target_user_id,
            "target_email": target_email,
            "digest_frequency": digest_frequency,
        }
        payload = {
            "source_kind": "notification",
            "source_id": source_id,
            "source_public_id": source_doc.get("public_id"),
            "source_title": source_doc.get("title"),
            "source_message": source_doc.get("message"),
            "scope": source_doc.get("scope"),
            "target_user_id": target_user_id,
            "target_email": target_email,
            "target_user_name": recipient.get("full_name"),
            "digest_frequency": digest_frequency,
            "scheduled_for": scheduled_for,
            "status": "queued",
            "updated_at": now,
            "schema_version": COMMUNICATION_DIGEST_SCHEMA_VERSION,
        }
        existing = await db.communication_digests.find_one(query)
        if existing is None:
            payload["created_at"] = now
            await db.communication_digests.insert_one(payload)
        else:
            payload["created_at"] = existing.get("created_at") or now
            await db.communication_digests.update_one(query, {"$set": payload}, upsert=True)

        label = "daily digest" if digest_frequency == "daily_digest" else "weekly digest"
        queued_results.append(
            {
                "user_id": target_user_id,
                "email": target_email,
                "status": "pending",
                "error": f"Queued for {label}",
                "sent_at": None,
                "metadata": {"digest_frequency": digest_frequency, "scheduled_for": scheduled_for.isoformat()},
            }
        )
    return queued_results


async def dispatch_due_notification_digests(*, limit: int = 200) -> int:
    now = _utcnow()
    rows = await db.communication_digests.find(
        {"status": "queued", "scheduled_for": {"$lte": now}}
    ).sort("scheduled_for", 1).to_list(length=max(limit, 1) * 10)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if len(grouped) >= limit and (str(row.get("target_user_id") or "").strip(), str(row.get("digest_frequency") or "")) not in grouped:
            break
        grouped[(str(row.get("target_user_id") or "").strip() or str(row.get("target_email") or "").strip().lower(), str(row.get("digest_frequency") or "daily_digest"))].append(row)

    processed = 0
    for (_recipient_key, digest_frequency), items in grouped.items():
        recipient = {
            "user_id": items[0].get("target_user_id"),
            "email": items[0].get("target_email"),
            "full_name": items[0].get("target_user_name"),
        }
        subject, body = build_notification_digest_email(
            digest_frequency=digest_frequency,
            items=items,
            generated_at=now,
        )
        results = await send_outbound_email_batch(subject=subject, body=body, recipients=[recipient])
        result = results[0] if results else {
            "user_id": recipient.get("user_id"),
            "email": recipient.get("email"),
            "status": "failed",
            "error": "Digest send returned no result",
            "sent_at": None,
        }

        digest_status = str(result.get("status") or "failed")
        for item in items:
            await db.communication_digests.update_one(
                {"_id": item["_id"]},
                {
                    "$set": {
                        "status": "sent" if digest_status == "sent" else "failed",
                        "sent_at": result.get("sent_at"),
                        "error": result.get("error"),
                        "updated_at": _utcnow(),
                        "schema_version": COMMUNICATION_DIGEST_SCHEMA_VERSION,
                    }
                },
            )
            await upsert_email_deliveries(
                source_kind="notification",
                source_id=str(item.get("source_id") or ""),
                source_public_id=item.get("source_public_id"),
                recipients=[recipient],
                results=[
                    {
                        "user_id": recipient.get("user_id"),
                        "email": recipient.get("email"),
                        "status": digest_status,
                        "error": result.get("error"),
                        "sent_at": result.get("sent_at"),
                        "metadata": {"digest_frequency": digest_frequency},
                    }
                ],
                metadata={"scope": item.get("scope"), "delivery_mode": digest_frequency},
            )
            processed += 1
    return processed


async def get_notification_digest_report() -> dict[str, Any]:
    rows = await db.communication_digests.find({}).to_list(length=5000)
    summary = {
        "queued_total": 0,
        "sent_total": 0,
        "failed_total": 0,
        "daily_total": 0,
        "weekly_total": 0,
    }
    for row in rows:
        status = str(row.get("status") or "").strip().lower()
        if status == "queued":
            summary["queued_total"] += 1
        elif status == "sent":
            summary["sent_total"] += 1
        elif status == "failed":
            summary["failed_total"] += 1

        frequency = str(row.get("digest_frequency") or "").strip().lower()
        if frequency == "daily_digest":
            summary["daily_total"] += 1
        elif frequency == "weekly_digest":
            summary["weekly_total"] += 1
    return summary
