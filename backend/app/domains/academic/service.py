from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.core.mongo import parse_object_id
from app.core.soft_delete import apply_is_active_filter, build_state_update
from app.models.courses import course_public
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate

from .repository import CourseRepository


class CourseService:
    def __init__(self, repository: CourseRepository | None = None):
        self.repository = repository or CourseRepository()

    async def list_courses(
        self,
        *,
        q: str | None,
        is_active: bool | None,
        skip: int,
        limit: int,
    ) -> list[CourseOut]:
        query = {}
        if q:
            query["$or"] = [
                {"name": {"$regex": q, "$options": "i"}},
                {"code": {"$regex": q, "$options": "i"}},
            ]
        apply_is_active_filter(query, is_active)

        items = await self.repository.list_courses(query, skip=skip, limit=limit)
        return [CourseOut(**course_public(item)) for item in items]

    async def get_course(self, *, course_id: str) -> CourseOut:
        item = await self.repository.get_course_by_id(parse_object_id(course_id))
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return CourseOut(**course_public(item))

    async def create_course(self, *, payload: CourseCreate) -> CourseOut:
        normalized_code = payload.code.strip().upper()
        existing = await self.repository.get_course_by_code(normalized_code)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course code already exists")

        document = {
            "name": payload.name.strip(),
            "code": normalized_code,
            "description": payload.description,
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
        result = await self.repository.create_course(document)
        created = await self.repository.get_course_by_id(result.inserted_id)
        if not created:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Course creation failed")
        return CourseOut(**course_public(created))

    async def update_course(self, *, course_id: str, payload: CourseUpdate) -> CourseOut:
        course_obj_id = parse_object_id(course_id)
        update_data = payload.model_dump(exclude_none=True)
        if "name" in update_data and update_data["name"]:
            update_data["name"] = update_data["name"].strip()
        if "code" in update_data and update_data["code"]:
            update_data["code"] = update_data["code"].strip().upper()
            duplicate = await self.repository.get_course_by_code(update_data["code"])
            if duplicate and duplicate.get("_id") != course_obj_id:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Course code already exists")
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields to update")

        result = await self.repository.update_course(course_obj_id, build_state_update(update_data))
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        updated = await self.repository.get_course_by_id(course_obj_id)
        if not updated:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return CourseOut(**course_public(updated))

    async def delete_course(self, *, course_id: str, deleted_by: str) -> dict[str, str]:
        result = await self.repository.archive_course(
            parse_object_id(course_id),
            deleted_by=deleted_by,
            deleted_at=datetime.now(timezone.utc),
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
        return {"message": "Course archived"}
