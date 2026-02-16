from datetime import datetime

from pydantic import BaseModel, Field


class YearCreate(BaseModel):
    course_id: str = Field(min_length=1)
    year_number: int = Field(ge=1, le=10)
    label: str = Field(min_length=1, max_length=80)


class YearUpdate(BaseModel):
    year_number: int | None = Field(default=None, ge=1, le=10)
    label: str | None = Field(default=None, min_length=1, max_length=80)
    is_active: bool | None = None


class YearOut(BaseModel):
    id: str
    course_id: str
    year_number: int
    label: str
    is_active: bool = True
    created_at: datetime | None = None
