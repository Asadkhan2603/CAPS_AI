from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class DepartmentCreate(BaseModel):
    department_id: str | None = Field(default=None, min_length=2, max_length=150)
    department_code: str | None = Field(default=None, min_length=2, max_length=60)
    department_name: str | None = Field(default=None, min_length=2, max_length=150)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    code: str | None = Field(default=None, min_length=2, max_length=60)
    faculty_id: str | None = Field(default=None, min_length=1)
    faculty_master_id: str | None = Field(default=None, min_length=2, max_length=120)
    faculty_code: str | None = Field(default=None, max_length=60)
    faculty_name: str | None = Field(default=None, max_length=150)
    university_master_id: str | None = Field(default=None, max_length=60)
    university_name: str | None = Field(default=None, max_length=150)
    university_code: str | None = Field(default=None, max_length=60)

    @model_validator(mode="after")
    def ensure_names(self):
        if not (self.department_name or self.name):
            raise ValueError("Department name is required")
        if not (self.department_code or self.code):
            raise ValueError("Department code is required")
        return self


class DepartmentUpdate(BaseModel):
    department_id: str | None = Field(default=None, min_length=2, max_length=150)
    department_code: str | None = Field(default=None, min_length=2, max_length=60)
    department_name: str | None = Field(default=None, min_length=2, max_length=150)
    name: str | None = Field(default=None, min_length=2, max_length=150)
    code: str | None = Field(default=None, min_length=2, max_length=60)
    faculty_id: str | None = Field(default=None, min_length=1)
    faculty_master_id: str | None = Field(default=None, min_length=2, max_length=120)
    faculty_code: str | None = Field(default=None, max_length=60)
    faculty_name: str | None = Field(default=None, max_length=150)
    university_master_id: str | None = Field(default=None, max_length=60)
    university_name: str | None = Field(default=None, max_length=150)
    university_code: str | None = Field(default=None, max_length=60)
    is_active: bool | None = None


class DepartmentOut(BaseModel):
    id: str
    department_id: str
    department_code: str
    department_name: str
    name: str
    code: str
    faculty_id: str | None = None
    faculty_master_id: str | None = None
    faculty_code: str | None = None
    faculty_name: str | None = None
    university_master_id: str | None = None
    university_name: str | None = None
    university_code: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1
