from typing import List

from fastapi import APIRouter, Depends, Query, status

from app.core.database import db
from app.core.security import require_permission, require_roles
from app.domains.academic.repository import CourseRepository
from app.domains.academic.service import CourseService
from app.schemas.course import CourseCreate, CourseOut, CourseUpdate
from app.services.audit import log_destructive_action_event
from app.services.governance import enforce_review_approval

router = APIRouter()
course_service = CourseService(CourseRepository(lambda: db))


@router.get('/', response_model=List[CourseOut])
async def list_courses(
    q: str | None = Query(default=None, min_length=1, max_length=100),
    is_active: bool | None = Query(default=True),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[CourseOut]:
    items: List[CourseOut] = await course_service.list_courses(
        q=q,
        is_active=is_active,
        skip=skip,
        limit=limit,
    )
    return items


@router.get('/{course_id}', response_model=CourseOut)
async def get_course(
    course_id: str,
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> CourseOut:
    return await course_service.get_course(course_id=course_id)


@router.post('/', response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(
    payload: CourseCreate,
    _current_user=Depends(require_permission("courses.manage")),
) -> CourseOut:
    return await course_service.create_course(payload=payload)


@router.put('/{course_id}', response_model=CourseOut)
async def update_course(
    course_id: str,
    payload: CourseUpdate,
    _current_user=Depends(require_permission("courses.manage")),
) -> CourseOut:
    return await course_service.update_course(course_id=course_id, payload=payload)


@router.delete('/{course_id}')
async def delete_course(
    course_id: str,
    review_id: str | None = Query(default=None),
    current_user=Depends(require_permission("courses.manage")),
) -> dict:
    actor_user_id = str(current_user.get("_id") or "") or None
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="courses.delete",
        entity_type="course",
        entity_id=course_id,
        stage="requested",
        detail="Course delete requested",
        review_id=review_id,
        metadata={"admin_type": current_user.get("admin_type")},
    )
    governance_completed = bool(await enforce_review_approval(
        current_user=current_user,
        review_id=review_id,
        action="courses.delete",
        entity_type="course",
        entity_id=course_id,
    ))
    result: dict[str, str] = await course_service.delete_course(
        course_id=course_id,
        deleted_by=str(current_user.get("_id")),
    )
    await log_destructive_action_event(
        actor_user_id=actor_user_id,
        action="courses.delete",
        entity_type="course",
        entity_id=course_id,
        stage="completed",
        detail="Course archived",
        review_id=review_id,
        governance_completed=governance_completed,
        outcome="archived",
        metadata={"admin_type": current_user.get("admin_type")},
    )
    return result
