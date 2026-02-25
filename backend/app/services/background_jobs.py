from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Iterable

from bson import ObjectId
from app.core.database import db
from app.core.mongo import parse_object_id
from app.services.analytics_snapshot import compute_platform_snapshot
from app.services.notifications import create_notification


async def _class_ids_for_year(year_id: str) -> list[str]:
    rows = await db.classes.find({"year_id": year_id, "is_active": True}, {"_id": 1}).to_list(length=5000)
    return [str(item.get("_id")) for item in rows if item.get("_id")]


async def _student_user_ids_for_class_ids(class_ids: Iterable[str]) -> list[str]:
    class_ids = [class_id for class_id in class_ids if class_id]
    if not class_ids:
        return []
    enrollments = await db.enrollments.find({"class_id": {"$in": class_ids}}).to_list(length=20000)
    student_ids = sorted({row.get("student_id") for row in enrollments if row.get("student_id")})
    if not student_ids:
        return []
    student_object_ids = [parse_object_id(sid) for sid in student_ids if ObjectId.is_valid(sid)]
    if not student_object_ids:
        return []
    student_rows = await db.students.find({"_id": {"$in": student_object_ids}}, {"email": 1}).to_list(length=len(student_object_ids))
    emails = sorted({(row.get("email") or "").strip().lower() for row in student_rows if row.get("email")})
    if not emails:
        return []
    users = await db.users.find({"email": {"$in": emails}}, {"_id": 1}).to_list(length=len(emails))
    return [str(user.get("_id")) for user in users if user.get("_id")]


async def _student_user_ids_for_subject(subject_id: str) -> list[str]:
    assignments = await db.assignments.find({"subject_id": subject_id}, {"class_id": 1}).to_list(length=5000)
    class_ids = sorted({row.get("class_id") for row in assignments if row.get("class_id")})
    return await _student_user_ids_for_class_ids(class_ids)


async def _target_user_ids_for_notice(notice: dict[str, Any]) -> list[str]:
    scope = notice.get("scope")
    scope_ref_id = notice.get("scope_ref_id")
    if scope == "college":
        rows = await db.users.find({"is_active": True}, {"_id": 1}).to_list(length=50000)
        return [str(row.get("_id")) for row in rows if row.get("_id")]
    if scope == "class" and scope_ref_id:
        return await _student_user_ids_for_class_ids([scope_ref_id])
    if scope == "year" and scope_ref_id:
        class_ids = await _class_ids_for_year(scope_ref_id)
        return await _student_user_ids_for_class_ids(class_ids)
    if scope == "subject" and scope_ref_id:
        return await _student_user_ids_for_subject(scope_ref_id)
    return []


async def fanout_notice_notifications(notice_id: str) -> None:
    try:
        notice = await db.notices.find_one({"_id": parse_object_id(notice_id), "is_active": True})
        if not notice:
            return
        target_user_ids = await _target_user_ids_for_notice(notice)
        if not target_user_ids:
            return
        for user_id in target_user_ids:
            await create_notification(
                title=notice.get("title") or "Announcement",
                message=notice.get("message") or "",
                priority=notice.get("priority") or "normal",
                scope="notice",
                target_user_id=user_id,
                created_by=notice.get("created_by"),
            )
        await db.notices.update_one(
            {"_id": notice["_id"]},
            {
                "$set": {
                    "fanout_dispatched_at": datetime.now(timezone.utc),
                    "fanout_count": len(target_user_ids),
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
