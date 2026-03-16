from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class ProgramCreate(BaseModel):
    program_id: str | None = Field(default=None, min_length=2, max_length=180)
    program_code: str | None = Field(default=None, min_length=2, max_length=80)
    program_name: str | None = Field(default=None, min_length=2, max_length=180)
    name: str | None = Field(default=None, min_length=2, max_length=180)
    code: str | None = Field(default=None, min_length=2, max_length=80)
    department_id: str = Field(min_length=1)
    department_master_id: str | None = Field(default=None, max_length=150)
    department_name: str | None = Field(default=None, max_length=180)
    department_code: str | None = Field(default=None, max_length=80)
    faculty_master_id: str | None = Field(default=None, max_length=120)
    faculty_code: str | None = Field(default=None, max_length=80)
    duration_years: int
    total_semesters: int | None = None
    degree_type: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def ensure_names(self):
        if not (self.program_name or self.name):
            raise ValueError("Program name is required")
        if not (self.program_code or self.code):
            raise ValueError("Program code is required")
        return self


class ProgramUpdate(BaseModel):
    program_id: str | None = Field(default=None, min_length=2, max_length=180)
    program_code: str | None = Field(default=None, min_length=2, max_length=80)
    program_name: str | None = Field(default=None, min_length=2, max_length=180)
    name: str | None = Field(default=None, min_length=2, max_length=180)
    code: str | None = Field(default=None, min_length=2, max_length=80)
    department_id: str | None = Field(default=None, min_length=1)
    department_master_id: str | None = Field(default=None, max_length=150)
    department_name: str | None = Field(default=None, max_length=180)
    department_code: str | None = Field(default=None, max_length=80)
    faculty_master_id: str | None = Field(default=None, max_length=120)
    faculty_code: str | None = Field(default=None, max_length=80)
    duration_years: int | None = None
    total_semesters: int | None = None
    degree_type: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ProgramOut(BaseModel):
    id: str
    program_id: str
    program_code: str
    program_name: str
    name: str
    code: str
    department_id: str
    department_master_id: str | None = None
    department_name: str | None = None
    department_code: str | None = None
    faculty_master_id: str | None = None
    faculty_code: str | None = None
    duration_years: int
    total_semesters: int
    degree_type: str | None = None
    description: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1
