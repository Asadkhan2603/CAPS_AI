from datetime import datetime

from pydantic import BaseModel, Field


class SubjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=500)


class SubjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    code: str | None = Field(default=None, min_length=2, max_length=30)
    description: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class SubjectOut(BaseModel):
    id: str
    name: str
    code: str
    description: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
    schema_version: int = 1
