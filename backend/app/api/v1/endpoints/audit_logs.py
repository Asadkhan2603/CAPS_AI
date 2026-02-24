from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, Query

from app.core.database import db
from app.core.security import require_roles
from app.models.audit_logs import audit_log_public
from app.schemas.audit_log import AuditLogOut

router = APIRouter()


def _sort_ts(value) -> float:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc).timestamp()
        return value.timestamp()
    return 0.0


@router.get('/', response_model=List[AuditLogOut])
async def list_audit_logs(
    actor_user_id: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    action: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    created_from: datetime | None = Query(default=None),
    created_to: datetime | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    _current_user=Depends(require_roles(['admin', 'teacher'])),
) -> List[AuditLogOut]:
    query = {}
    if actor_user_id:
        query['actor_user_id'] = actor_user_id
    if entity_type:
        query['entity_type'] = entity_type
    if resource_type:
        query['resource_type'] = resource_type
    if action:
        query['action'] = action
    if severity:
        query['severity'] = severity
    if created_from or created_to:
        query['created_at'] = {}
        if created_from:
            query['created_at']['$gte'] = created_from
        if created_to:
            query['created_at']['$lte'] = created_to

    cursor = db.audit_logs.find(query)
    if hasattr(cursor, 'sort'):
        cursor = cursor.sort('created_at', -1).skip(skip).limit(limit)
        items = await cursor.to_list(length=limit)
    else:
        items = await cursor.skip(skip).limit(limit).to_list(length=limit)
        items.sort(key=lambda item: _sort_ts(item.get('created_at')), reverse=True)
    return [AuditLogOut(**audit_log_public(item)) for item in items]
