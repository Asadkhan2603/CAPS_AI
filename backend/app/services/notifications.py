from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable

from app.core.database import db
from app.core.schema_versions import NOTIFICATION_SCHEMA_VERSION
from app.services.communication_deliveries import (
    get_delivery_summaries,
    resolve_all_active_user_recipients,
    resolve_user_recipients,
    upsert_email_deliveries,
    upsert_in_app_delivery_results,
    upsert_in_app_deliveries,
)
from app.services.communication_digests import queue_notification_digests
from app.services.communication_email_content import build_notification_email_body
from app.services.communication_preferences import partition_notification_recipients_by_preferences
from app.services.outbound_email import send_outbound_email_batch
from app.services.public_ids import build_public_id, persist_public_id


async def create_notification(
    *,
    title: str,
    message: str,
    priority: str = "normal",
    scope: str = "global",
    target_user_id: str | None = None,
    created_by: str | None = None,
    track_delivery: bool = True,
    send_email: bool | None = None,
) -> Dict[str, Any]:
    document = {
        "title": title.strip(),
        "message": message.strip(),
        "priority": priority,
        "scope": scope,
        "target_user_id": target_user_id,
        "created_by": created_by,
        "is_read": False,
        "created_at": datetime.now(timezone.utc),
        "schema_version": NOTIFICATION_SCHEMA_VERSION,
    }
    persist_public_id(document, kind="notification")
    result = await db.notifications.insert_one(document)
    public_id = build_public_id("notification", {**document, "_id": result.inserted_id}, prefer_existing=False)
    if public_id:
        await db.notifications.update_one({"_id": result.inserted_id}, {"$set": {"public_id": public_id}})
    created = await db.notifications.find_one({"_id": result.inserted_id})
    if created and track_delivery:
        recipients = (
            await resolve_user_recipients([target_user_id])
            if target_user_id
            else await resolve_all_active_user_recipients()
        )
        partitioned = await partition_notification_recipients_by_preferences(recipients=recipients, scope=scope)
        if partitioned["in_app_recipients"]:
            await upsert_in_app_deliveries(
                source_kind="notification",
                source_id=str(result.inserted_id),
                source_public_id=public_id,
                recipients=partitioned["in_app_recipients"],
                metadata={"scope": scope, "priority": priority},
            )
        if partitioned["in_app_skips"]:
            await upsert_in_app_delivery_results(
                source_kind="notification",
                source_id=str(result.inserted_id),
                source_public_id=public_id,
                recipients=recipients,
                results=partitioned["in_app_skips"],
                metadata={"scope": scope, "priority": priority},
            )
        if send_email if send_email is not None else track_delivery:
            email_results = list(partitioned["email_skips"])
            if partitioned["instant_email_recipients"]:
                email_results.extend(
                    await send_outbound_email_batch(
                        subject=title.strip(),
                        body=build_notification_email_body(title=title, message=message, scope=scope),
                        recipients=partitioned["instant_email_recipients"],
                    )
                )
            for digest_frequency, digest_recipients in partitioned["digest_recipients"].items():
                if digest_recipients:
                    email_results.extend(
                        await queue_notification_digests(
                            source_doc=created,
                            recipients=digest_recipients,
                            digest_frequency=digest_frequency,
                        )
                    )
            await upsert_email_deliveries(
                source_kind="notification",
                source_id=str(result.inserted_id),
                source_public_id=public_id,
                recipients=recipients,
                results=email_results,
                metadata={"scope": scope, "priority": priority},
            )
        summaries = await get_delivery_summaries(source_kind="notification", source_ids=[str(result.inserted_id)])
        created["delivery_summary"] = summaries.get(str(result.inserted_id))
    return created or document


async def create_notifications_bulk(
    *,
    title: str,
    message: str,
    priority: str = "normal",
    scope: str = "global",
    target_user_ids: Iterable[str],
    created_by: str | None = None,
    batch_size: int = 1000,
    track_delivery: bool = True,
    send_email: bool | None = None,
) -> int:
    normalized_title = title.strip()
    normalized_message = message.strip()
    normalized_target_user_ids = [str(target_user_id) for target_user_id in target_user_ids if target_user_id]
    pending: list[dict[str, Any]] = []
    inserted_rows: list[dict[str, Any]] = []
    inserted = 0
    safe_batch_size = max(100, min(batch_size, 5000))

    for target_user_id in normalized_target_user_ids:
        pending.append(
            persist_public_id(
                {
                    "title": normalized_title,
                    "message": normalized_message,
                    "priority": priority,
                    "scope": scope,
                    "target_user_id": target_user_id,
                    "created_by": created_by,
                    "is_read": False,
                    "created_at": datetime.now(timezone.utc),
                    "schema_version": NOTIFICATION_SCHEMA_VERSION,
                },
                kind="notification",
            )
        )
        if len(pending) >= safe_batch_size:
            result = await db.notifications.insert_many(pending, ordered=False)
            for inserted_id, source in zip(result.inserted_ids, pending):
                public_id = build_public_id("notification", {**source, "_id": inserted_id}, prefer_existing=False)
                if public_id:
                    await db.notifications.update_one({"_id": inserted_id}, {"$set": {"public_id": public_id}})
                inserted_rows.append({**source, "_id": inserted_id, "public_id": public_id})
            inserted += len(result.inserted_ids)
            pending = []

    if pending:
        result = await db.notifications.insert_many(pending, ordered=False)
        for inserted_id, source in zip(result.inserted_ids, pending):
            public_id = build_public_id("notification", {**source, "_id": inserted_id}, prefer_existing=False)
            if public_id:
                await db.notifications.update_one({"_id": inserted_id}, {"$set": {"public_id": public_id}})
            inserted_rows.append({**source, "_id": inserted_id, "public_id": public_id})
        inserted += len(result.inserted_ids)
        pending = []

    if track_delivery:
        recipient_rows = await resolve_user_recipients(normalized_target_user_ids)
        recipient_by_user_id = {
            str(recipient.get("user_id") or ""): recipient
            for recipient in recipient_rows
            if recipient.get("user_id")
        }
        for row in inserted_rows:
            current_public_id = row.get("public_id")
            recipient = recipient_by_user_id.get(str(row.get("target_user_id") or ""))
            if not recipient:
                continue
            partitioned = await partition_notification_recipients_by_preferences(recipients=[recipient], scope=scope)
            if partitioned["in_app_recipients"]:
                await upsert_in_app_deliveries(
                    source_kind="notification",
                    source_id=str(row["_id"]),
                    source_public_id=current_public_id,
                    recipients=partitioned["in_app_recipients"],
                    metadata={"scope": scope, "priority": priority},
                )
            if partitioned["in_app_skips"]:
                await upsert_in_app_delivery_results(
                    source_kind="notification",
                    source_id=str(row["_id"]),
                    source_public_id=current_public_id,
                    recipients=[recipient],
                    results=partitioned["in_app_skips"],
                    metadata={"scope": scope, "priority": priority},
                )
            if send_email if send_email is not None else track_delivery:
                email_results = list(partitioned["email_skips"])
                if partitioned["instant_email_recipients"]:
                    email_results.extend(
                        await send_outbound_email_batch(
                            subject=normalized_title,
                            body=build_notification_email_body(
                                title=normalized_title,
                                message=normalized_message,
                                scope=scope,
                            ),
                            recipients=partitioned["instant_email_recipients"],
                        )
                    )
                for digest_frequency, digest_recipients in partitioned["digest_recipients"].items():
                    if digest_recipients:
                        email_results.extend(
                            await queue_notification_digests(
                                source_doc=row,
                                recipients=digest_recipients,
                                digest_frequency=digest_frequency,
                            )
                        )
                await upsert_email_deliveries(
                    source_kind="notification",
                    source_id=str(row["_id"]),
                    source_public_id=current_public_id,
                    recipients=[recipient],
                    results=email_results,
                    metadata={"scope": scope, "priority": priority},
                )
    return inserted
