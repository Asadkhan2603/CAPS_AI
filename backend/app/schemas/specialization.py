from datetime import datetime

from pydantic import BaseModel, Field


class SpecializationCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    code: str = Field(min_length=2, max_length=120)
    program_id: str = Field(min_length=1)
    description: str | None = Field(default=None, max_length=300)


class SpecializationUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    code: str | None = Field(default=None, min_length=2, max_length=120)
    program_id: str | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, max_length=300)
    is_active: bool | None = None


class SpecializationOut(BaseModel):
    id: str
    name: str
    code: str
    program_id: str
    description: str | None = None
    is_active: bool = True
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    created_at: datetime | None = None
