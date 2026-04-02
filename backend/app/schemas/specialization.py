from datetime import datetime

from pydantic import BaseModel, Field, model_validator


class SpecializationCreate(BaseModel):
    specialization_id: str | None = Field(default=None, min_length=2, max_length=220)
    specialization_code: str | None = Field(default=None, min_length=2, max_length=120)
    specialization_name: str | None = Field(default=None, min_length=2, max_length=180)
    name: str | None = Field(default=None, min_length=2, max_length=180)
    code: str | None = Field(default=None, min_length=2, max_length=120)
    program_id: str = Field(min_length=1)
    program_master_id: str | None = Field(default=None, max_length=180)
    program_name: str | None = Field(default=None, max_length=180)
    program_code: str | None = Field(default=None, max_length=120)
    department_master_id: str | None = Field(default=None, max_length=150)
    department_code: str | None = Field(default=None, max_length=80)
    faculty_master_id: str | None = Field(default=None, max_length=120)
    faculty_code: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def ensure_names(self):
        if not (self.specialization_name or self.name):
            raise ValueError("Specialization name is required")
        if not (self.specialization_code or self.code):
            raise ValueError("Specialization code is required")
        return self


class SpecializationUpdate(BaseModel):
    specialization_id: str | None = Field(default=None, min_length=2, max_length=220)
    specialization_code: str | None = Field(default=None, min_length=2, max_length=120)
    specialization_name: str | None = Field(default=None, min_length=2, max_length=180)
    name: str | None = Field(default=None, min_length=2, max_length=180)
    code: str | None = Field(default=None, min_length=2, max_length=120)
    program_id: str | None = Field(default=None, min_length=1)
    program_master_id: str | None = Field(default=None, max_length=180)
    program_name: str | None = Field(default=None, max_length=180)
    program_code: str | None = Field(default=None, max_length=120)
    department_master_id: str | None = Field(default=None, max_length=150)
    department_code: str | None = Field(default=None, max_length=80)
    faculty_master_id: str | None = Field(default=None, max_length=120)
    faculty_code: str | None = Field(default=None, max_length=80)
    description: str | None = Field(default=None, max_length=300)
    is_active: bool | None = None


class SpecializationOut(BaseModel):
    id: str
    specialization_id: str
    specialization_code: str
    specialization_name: str
    public_id: str | None = None
    display_label: str | None = None
    name: str
    code: str
    program_id: str
    program_master_id: str | None = None
    program_name: str | None = None
    program_code: str | None = None
    department_master_id: str | None = None
    department_code: str | None = None
    faculty_master_id: str | None = None
    faculty_code: str | None = None
    description: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1
