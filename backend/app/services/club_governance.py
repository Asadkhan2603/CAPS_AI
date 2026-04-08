from datetime import datetime, timezone

from bson import ObjectId

from app.core.database import db
from app.core.mongo import parse_object_id
from app.core.schema_versions import CLUB_MEMBER_SCHEMA_VERSION, CLUB_SCHEMA_VERSION, USER_SCHEMA_VERSION
from app.services.public_ids import build_public_id, persist_public_id


async def _find_student_user(user_id: str):
    if not user_id or not ObjectId.is_valid(user_id):
        return None
    return await db.users.find_one({"_id": parse_object_id(user_id), "role": "student"})


async def _update_student_president_scope(student_user_id: str, club_id: str | None) -> None:
    student = await _find_student_user(student_user_id)
    if not student:
        return

    extended_roles = [role for role in list(student.get("extended_roles") or []) if role != "club_president"]
    role_scope = dict(student.get("role_scope") or {})
    role_scope.pop("club_president", None)

    if club_id:
        extended_roles.append("club_president")
        role_scope["club_president"] = {"club_id": club_id}

    await db.users.update_one(
        {"_id": parse_object_id(student_user_id)},
        {
            "$set": {
                "extended_roles": extended_roles,
                "role_scope": role_scope,
                "schema_version": USER_SCHEMA_VERSION,
            }
        },
    )


async def _demote_president_memberships(club_id: str, except_student_user_id: str | None = None) -> None:
    query = {"club_id": club_id, "role": "president"}
    if except_student_user_id:
        query["student_user_id"] = {"$ne": except_student_user_id}
    await db.club_members.update_many(
        query,
        {"$set": {"role": "member", "schema_version": CLUB_MEMBER_SCHEMA_VERSION}},
    )


async def _ensure_president_membership(club_id: str, student_user: dict) -> None:
    now = datetime.now(timezone.utc)
    student_user_id = str(student_user.get("_id"))
    existing = await db.club_members.find_one({"club_id": club_id, "student_user_id": student_user_id})

    if existing:
        await db.club_members.update_one(
            {"_id": existing["_id"]},
            {
                "$set": {
                    "student_name": student_user.get("full_name"),
                    "student_email": student_user.get("email"),
                    "role": "president",
                    "status": "active",
                    "left_at": None,
                    "joined_at": existing.get("joined_at") or now,
                    "schema_version": CLUB_MEMBER_SCHEMA_VERSION,
                }
            },
        )
        return

    membership = persist_public_id(
        {
            "club_id": club_id,
            "student_user_id": student_user_id,
            "student_name": student_user.get("full_name"),
            "student_email": student_user.get("email"),
            "role": "president",
            "status": "active",
            "joined_at": now,
            "left_at": None,
            "schema_version": CLUB_MEMBER_SCHEMA_VERSION,
        },
        kind="club_member",
    )
    result = await db.club_members.insert_one(membership)
    public_id = build_public_id(
        "club_member",
        {"club_id": club_id, "_id": result.inserted_id},
        prefer_existing=False,
    )
    if public_id:
        await db.club_members.update_one(
            {"_id": result.inserted_id},
            {"$set": {"public_id": public_id}},
        )


async def assign_student_as_club_president(
    student_user_id: str,
    club_id: str,
    *,
    sync_target_user_record: bool = True,
) -> None:
    student = await _find_student_user(student_user_id)
    if not student:
        return

    club = await db.clubs.find_one({"_id": parse_object_id(club_id)})
    if not club:
        return

    current_president_user_id = club.get("president_user_id")
    if current_president_user_id and current_president_user_id != student_user_id:
        await _update_student_president_scope(current_president_user_id, None)

    previous_clubs = await db.clubs.find(
        {"president_user_id": student_user_id, "_id": {"$ne": parse_object_id(club_id)}}
    ).to_list(length=1000)
    for previous_club in previous_clubs:
        previous_club_id = str(previous_club.get("_id"))
        await db.clubs.update_one(
            {"_id": previous_club["_id"]},
            {"$set": {"president_user_id": None, "schema_version": CLUB_SCHEMA_VERSION}},
        )
        await _demote_president_memberships(previous_club_id)

    await db.clubs.update_one(
        {"_id": parse_object_id(club_id)},
        {"$set": {"president_user_id": student_user_id, "schema_version": CLUB_SCHEMA_VERSION}},
    )
    await _demote_president_memberships(club_id, except_student_user_id=student_user_id)
    await _ensure_president_membership(club_id, student)

    if sync_target_user_record:
        await _update_student_president_scope(student_user_id, club_id)


async def clear_student_club_president(
    student_user_id: str,
    club_id: str | None = None,
    *,
    sync_target_user_record: bool = True,
) -> None:
    if club_id:
        clubs = await db.clubs.find({"_id": parse_object_id(club_id), "president_user_id": student_user_id}).to_list(length=10)
    else:
        clubs = await db.clubs.find({"president_user_id": student_user_id}).to_list(length=1000)

    for club in clubs:
        current_club_id = str(club.get("_id"))
        await db.clubs.update_one(
            {"_id": club["_id"]},
            {"$set": {"president_user_id": None, "schema_version": CLUB_SCHEMA_VERSION}},
        )
        await db.club_members.update_many(
            {"club_id": current_club_id, "student_user_id": student_user_id, "role": "president"},
            {"$set": {"role": "member", "schema_version": CLUB_MEMBER_SCHEMA_VERSION}},
        )

    if sync_target_user_record:
        await _update_student_president_scope(student_user_id, None)
