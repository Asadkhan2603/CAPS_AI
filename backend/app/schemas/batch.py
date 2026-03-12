from datetime import datetime

from pydantic import BaseModel, Field


class BatchCreate(BaseModel):
    program_id: str = Field(min_length=1)
    specialization_id: str | None = None
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=40)
    start_year: int | None = Field(default=None, ge=2000, le=2100)
    end_year: int | None = Field(default=None, ge=2000, le=2100)


class BatchUpdate(BaseModel):
    program_id: str | None = Field(default=None, min_length=1)
    specialization_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=80)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    start_year: int | None = Field(default=None, ge=2000, le=2100)
    end_year: int | None = Field(default=None, ge=2000, le=2100)
    is_active: bool | None = None


class BatchOut(BaseModel):
    id: str
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str
    specialization_id: str | None = None
    name: str
    code: str
    start_year: int | None = None
    end_year: int | None = None
    academic_span_label: str | None = None
    university_name: str | None = None
    university_code: str | None = None
    auto_generated: bool = False
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1
