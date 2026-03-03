from datetime import datetime

from pydantic import BaseModel, Field


class GroupCreate(BaseModel):
    section_id: str = Field(min_length=1)
    name: str = Field(min_length=1, max_length=80)
    code: str = Field(min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=300)


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    code: str | None = Field(default=None, min_length=1, max_length=40)
    description: str | None = Field(default=None, max_length=300)
    is_active: bool | None = None


class GroupOut(BaseModel):
    id: str
    section_id: str
    name: str
    code: str
    description: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
