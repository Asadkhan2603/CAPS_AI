from __future__ import annotations

from typing import Any

from app.core.database import db
from app.core.mongo import parse_object_id


def is_admin(user: dict[str, Any]) -> bool:
    return user.get("role") == "admin"


def is_teacher(user: dict[str, Any]) -> bool:
    return user.get("role") == "teacher"


def is_assigned_club_coordinator(user: dict[str, Any], club: dict[str, Any]) -> bool:
    if not is_teacher(user):
        return False
    return club.get("coordinator_user_id") == str(user.get("_id"))


def can_manage_club(user: dict[str, Any], club: dict[str, Any]) -> bool:
    if is_admin(user):
        return True
    return is_assigned_club_coordinator(user, club)


def can_manage_club_event(user: dict[str, Any], club: dict[str, Any]) -> bool:
    if can_manage_club(user, club):
        return True
    if user.get("role") == "student":
        return club.get("president_user_id") == str(user.get("_id"))
    return False


async def teacher_managed_club_ids(teacher_user_id: str) -> list[str]:
    clubs = await db.clubs.find({"coordinator_user_id": teacher_user_id}).to_list(length=1000)
    return [str(item.get("_id")) for item in clubs if item.get("_id")]


async def teacher_managed_event_ids(teacher_user_id: str) -> list[str]:
    club_ids = await teacher_managed_club_ids(teacher_user_id)
    if not club_ids:
        return []
    events = await db.club_events.find({"club_id": {"$in": club_ids}}).to_list(length=2000)
    return [str(item.get("_id")) for item in events if item.get("_id")]


async def student_is_club_president_for_event(student_user_id: str, event_id: str) -> bool:
    event = await db.club_events.find_one({"_id": parse_object_id(event_id)})
    if not event:
        return False
    club = await db.clubs.find_one({"_id": parse_object_id(event.get("club_id"))})
    if not club:
        return False
    return club.get("president_user_id") == student_user_id
