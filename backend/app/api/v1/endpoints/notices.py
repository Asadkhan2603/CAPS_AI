from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import db
from app.core.security import require_roles
from app.models.notices import notice_public
from app.schemas.notice import NoticeCreate, NoticeOut
from app.services.audit import log_audit_event

router = APIRouter()


def _can_publish_scope(current_user: dict, scope: str) -> bool:
    if current_user.get('role') == 'admin':
        return True
    if current_user.get('role') != 'teacher':
        return False
    extensions = current_user.get('extended_roles', [])
    if scope == 'college':
        return False
    if scope == 'year':
        return 'year_head' in extensions
    if scope == 'class':
        return 'class_coordinator' in extensions
    if scope == 'subject':
        return True
    return False


@router.get('/', response_model=List[NoticeOut])
async def list_notices(
    scope: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    include_expired: bool = Query(default=False),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user=Depends(require_roles(['admin', 'teacher', 'student'])),
) -> List[NoticeOut]:
    query = {'is_active': True}
    if scope:
        query['scope'] = scope
    if priority:
        query['priority'] = priority

    now = datetime.now(timezone.utc)
    items = await db.notices.find(query).skip(skip).limit(limit).to_list(length=limit)
    if not include_expired:
        items = [item for item in items if not item.get('expires_at') or item.get('expires_at') > now]

    if current_user.get('role') == 'student':
        # Until student-to-class/year/subject targeting is fully mapped,
        # keep student visibility restricted to college-wide notices.
        items = [item for item in items if item.get('scope') == 'college']

    return [NoticeOut(**notice_public(item)) for item in items]


@router.post('/', response_model=NoticeOut, status_code=status.HTTP_201_CREATED)
async def create_notice(
    payload: NoticeCreate,
    current_user=Depends(require_roles(['admin', 'teacher'])),
) -> NoticeOut:
    if not _can_publish_scope(current_user, payload.scope):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail='Not allowed to publish this notice scope')

    document = {
        'title': payload.title.strip(),
        'message': payload.message.strip(),
        'priority': payload.priority,
        'scope': payload.scope,
        'scope_ref_id': payload.scope_ref_id,
        'expires_at': payload.expires_at,
        'created_by': str(current_user['_id']),
        'is_active': True,
        'created_at': datetime.now(timezone.utc),
    }
    result = await db.notices.insert_one(document)
    created = await db.notices.find_one({'_id': result.inserted_id})

    await log_audit_event(
        actor_user_id=str(current_user['_id']),
        action='create',
        entity_type='notice',
        entity_id=str(result.inserted_id),
        detail=f"Created {payload.priority} notice with scope {payload.scope}",
    )
    return NoticeOut(**notice_public(created))
