from datetime import datetime

from pydantic import BaseModel, Field


class AuditLogOut(BaseModel):
    id: str
    actor_user_id: str | None = None
    action: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    entity_id: str | None = None
    detail: str | None = None
    created_at: datetime | None = None
