from typing import List

from fastapi import APIRouter, Depends, Query

from app.core.database import db
from app.core.security import require_roles
from app.models.audit_logs import audit_log_public
from app.schemas.audit_log import AuditLogOut

router = APIRouter()


@router.get('/', response_model=List[AuditLogOut])
async def list_audit_logs(
    actor_user_id: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[AuditLogOut]:
    query = {}
    if actor_user_id:
        query['actor_user_id'] = actor_user_id
    if entity_type:
        query['entity_type'] = entity_type
    if action:
        query['action'] = action

    cursor = db.audit_logs.find(query).skip(skip).limit(limit)
    items = await cursor.to_list(length=limit)
    return [AuditLogOut(**audit_log_public(item)) for item in items]
