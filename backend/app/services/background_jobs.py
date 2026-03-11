from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from bson import ObjectId
from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.analytics_snapshot import compute_platform_snapshot
from app.services.notifications import create_notifications_bulk


async def _class_ids_for_batch(batch_id: str) -> list[str]:
    class_object_ids = await db.classes.distinct("_id", {"batch_id": batch_id, "is_active": True})
    return [str(item) for item in class_object_ids if item]


async def _student_user_ids_for_class_ids(class_ids: Iterable[str]) -> list[str]:
    class_ids = [class_id for class_id in class_ids if class_id]
    if not class_ids:
        return []
    student_ids = sorted(
        {
            value
            for value in await db.enrollments.distinct("student_id", {"class_id": {"$in": class_ids}})
            if isinstance(value, str) and value
        }
    )
    if not student_ids:
        return []
    student_object_ids = [parse_object_id(sid) for sid in student_ids if ObjectId.is_valid(sid)]
    if not student_object_ids:
        return []
    emails = sorted(
        {
            value.strip().lower()
            for value in await db.students.distinct("email", {"_id": {"$in": student_object_ids}})
            if isinstance(value, str) and value.strip()
        }
    )
    if not emails:
        return []
    user_object_ids = await db.users.distinct("_id", {"email": {"$in": emails}, "is_active": True})
    return [str(item) for item in user_object_ids if item]


async def _student_user_ids_for_subject(subject_id: str) -> list[str]:
    class_ids = sorted(
        {
            value
            for value in await db.assignments.distinct("class_id", {"subject_id": subject_id})
            if isinstance(value, str) and value
        }
    )
    return await _student_user_ids_for_class_ids(class_ids)


async def _target_user_ids_for_notice(notice: dict[str, Any]) -> list[str]:
    scope = notice.get("scope")
    scope_ref_id = notice.get("scope_ref_id")
    if scope == "class" and scope_ref_id:
        return await _student_user_ids_for_class_ids([scope_ref_id])
    if scope == "batch" and scope_ref_id:
        class_ids = await _class_ids_for_batch(scope_ref_id)
        return await _student_user_ids_for_class_ids(class_ids)
    if scope == "subject" and scope_ref_id:
        return await _student_user_ids_for_subject(scope_ref_id)
    return []


async def fanout_notice_notifications(notice_id: str) -> None:
    try:
        notice = await db.notices.find_one({"_id": parse_object_id(notice_id), "is_active": True})
        if not notice:
            return
        scope = notice.get("scope")
        target_user_ids: list[str] = []

        if scope == "college":
            # Stream recipients in chunks to avoid loading entire user base into memory.
            cursor = db.users.find({"is_active": True}, {"_id": 1}).batch_size(2000)
            buffered_ids: list[str] = []
            inserted = 0
            async for user in cursor:
                user_id = user.get("_id")
                if not user_id:
                    continue
                buffered_ids.append(str(user_id))
                if len(buffered_ids) >= 2000:
                    inserted += await create_notifications_bulk(
                        title=notice.get("title") or "Announcement",
                        message=notice.get("message") or "",
                        priority=notice.get("priority") or "normal",
                        scope="notice",
                        target_user_ids=buffered_ids,
                        created_by=notice.get("created_by"),
                        batch_size=1000,
                    )
                    buffered_ids = []
            if buffered_ids:
                inserted += await create_notifications_bulk(
                    title=notice.get("title") or "Announcement",
                    message=notice.get("message") or "",
                    priority=notice.get("priority") or "normal",
                    scope="notice",
                    target_user_ids=buffered_ids,
                    created_by=notice.get("created_by"),
                    batch_size=1000,
                )
            fanout_count = inserted
        else:
            target_user_ids = await _target_user_ids_for_notice(notice)
            if not target_user_ids:
                return
            fanout_count = await create_notifications_bulk(
                title=notice.get("title") or "Announcement",
                message=notice.get("message") or "",
                priority=notice.get("priority") or "normal",
                scope="notice",
                target_user_ids=target_user_ids,
                created_by=notice.get("created_by"),
                batch_size=1000,
            )
        await db.notices.update_one(
            {"_id": notice["_id"]},
            {
                "$set": {
                    "fanout_dispatched_at": datetime.now(timezone.utc),
                    "fanout_count": fanout_count,
                }
            },
        )
    except Exception:
        # Background jobs must never break request flow.
        return


async def run_daily_analytics_snapshot_job() -> None:
    try:
        await compute_platform_snapshot()
    except Exception:
        return


async def dispatch_scheduled_notice_notifications(*, limit: int = 200) -> int:
    try:
        now = datetime.now(timezone.utc)
        rows = await db.notices.find(
            {
                "is_active": True,
                "scheduled_at": {"$lte": now},
                "$or": [
                    {"fanout_dispatched_at": {"$exists": False}},
                    {"fanout_dispatched_at": None},
                ],
            },
            {"_id": 1},
        ).sort("scheduled_at", 1).limit(limit).to_list(length=limit)
        dispatched = 0
        for row in rows:
            notice_id = row.get("_id")
            if not notice_id:
                continue
            await fanout_notice_notifications(str(notice_id))
            dispatched += 1
        return dispatched
    except Exception:
        return 0
