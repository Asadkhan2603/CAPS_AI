from datetime import datetime

from pydantic import BaseModel, Field


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=2, max_length=100)
    roll_number: str = Field(min_length=1, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    user_id: str | None = None
    class_id: str | None = None
    group_id: str | None = None


class StudentUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=100)
    roll_number: str | None = Field(default=None, min_length=1, max_length=30)
    email: str | None = Field(default=None, max_length=255)
    user_id: str | None = None
    class_id: str | None = None
    group_id: str | None = None
    is_active: bool | None = None


class StudentOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    full_name: str
    roll_number: str
    email: str | None = None
    user_id: str | None = None
    class_id: str | None = None
    group_id: str | None = None
    canonical_class_id: str | None = None
    canonical_group_id: str | None = None
    placement_source: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    schema_version: int = 1
