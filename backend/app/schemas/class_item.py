from datetime import datetime

from pydantic import BaseModel, Field


class ClassCreate(BaseModel):
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    specialization_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    name: str = Field(min_length=1, max_length=100)
    faculty_name: str | None = Field(default=None, max_length=120)
    branch_name: str | None = Field(default=None, max_length=120)
    class_coordinator_user_id: str | None = None


class ClassUpdate(BaseModel):
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    specialization_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    name: str | None = Field(default=None, min_length=1, max_length=100)
    faculty_name: str | None = Field(default=None, max_length=120)
    branch_name: str | None = Field(default=None, max_length=120)
    class_coordinator_user_id: str | None = None
    is_active: bool | None = None


class ClassOut(BaseModel):
    id: str
    faculty_id: str | None = None
    department_id: str | None = None
    program_id: str | None = None
    specialization_id: str | None = None
    course_id: str | None = None
    year_id: str | None = None
    batch_id: str | None = None
    semester_id: str | None = None
    name: str
    faculty_name: str | None = None
    branch_name: str | None = None
    class_coordinator_user_id: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
