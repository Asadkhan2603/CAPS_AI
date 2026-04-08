from datetime import datetime

from pydantic import BaseModel, Field


class SharedQueueViewFilters(BaseModel):
    search: str = Field(default="", max_length=120)
    status: str = Field(default="all", max_length=40)
    page_size: int = Field(default=8, ge=1, le=100)


class SharedQueueViewCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    filters: SharedQueueViewFilters


class SharedQueueViewOut(BaseModel):
    id: str
    scope_type: str
    scope_id: str
    queue_type: str
    name: str
    filters: SharedQueueViewFilters
    created_by_user_id: str | None = None
    created_by_label: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1


class SharedQueueSnapshotOut(BaseModel):
    id: str
    scope_type: str
    scope_id: str
    queue_type: str
    total: int = 0
    pending: int = 0
    waitlisted: int = 0
    fresh: int = 0
    aging: int = 0
    stale: int = 0
    signature: str | None = None
    captured_at: datetime | None = None
    source_action: str | None = None
    changed_by_user_id: str | None = None
    changed_by_label: str | None = None
    schema_version: int = 1
