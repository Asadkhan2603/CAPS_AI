from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from app.core.database import db as core_db


class CourseRepository:
    def __init__(self, db_provider: Callable[[], Any] | None = None):
        self._db_provider = db_provider

    @property
    def _db(self):
        return self._db_provider() if self._db_provider else core_db

    async def list_courses(self, query: dict[str, Any], *, skip: int, limit: int) -> list[dict[str, Any]]:
        cursor = self._db.courses.find(query).skip(skip).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_course_by_id(self, course_obj_id) -> dict[str, Any] | None:
        return await self._db.courses.find_one({"_id": course_obj_id})

    async def get_course_by_code(self, code: str) -> dict[str, Any] | None:
        return await self._db.courses.find_one({"code": code})

    async def create_course(self, document: dict[str, Any]):
        return await self._db.courses.insert_one(document)

    async def update_course(self, course_obj_id, set_data: dict[str, Any]):
        return await self._db.courses.update_one({"_id": course_obj_id}, {"$set": set_data})

    async def archive_course(self, course_obj_id, *, deleted_by: str, deleted_at: datetime):
        return await self._db.courses.update_one(
            {"_id": course_obj_id, "is_active": True},
            {
                "$set": {
                    "is_active": False,
                    "is_deleted": True,
                    "deleted_at": deleted_at,
                    "deleted_by": deleted_by,
                }
            },
        )
