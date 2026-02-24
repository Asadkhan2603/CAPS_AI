from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogOut(BaseModel):
    id: str
    actor_user_id: str | None = None
    action: str = Field(min_length=1)
    action_type: str | None = None
    entity_type: str = Field(min_length=1)
    resource_type: str | None = None
    entity_id: str | None = None
    detail: str | None = None
    old_value: dict | None = None
    new_value: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    severity: str | None = None
    created_at: datetime | None = None
