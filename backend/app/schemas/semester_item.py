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
    public_id: str | None = None
    display_label: str | None = None
    batch_id: str
    batch_name: str | None = None
    batch_code: str | None = None
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    program_name: str | None = None
    program_code: str | None = None
    specialization_id: str | None = None
    specialization_name: str | None = None
    specialization_code: str | None = None
    semester_number: int
    label: str
    academic_year_start: int | None = None
    academic_year_end: int | None = None
    academic_year_label: str | None = None
    university_name: str | None = None
    university_code: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1
