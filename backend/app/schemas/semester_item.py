from datetime import datetime

from pydantic import BaseModel, Field


class SemesterCreate(BaseModel):
    batch_id: str = Field(min_length=1)
    semester_number: int = Field(ge=1, le=12)
    label: str = Field(min_length=1, max_length=80)


class SemesterUpdate(BaseModel):
    batch_id: str | None = Field(default=None, min_length=1)
    semester_number: int | None = Field(default=None, ge=1, le=12)
    label: str | None = Field(default=None, min_length=1, max_length=80)
    is_active: bool | None = None


class SemesterOut(BaseModel):
    id: str
    batch_id: str
    semester_number: int
    label: str
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
