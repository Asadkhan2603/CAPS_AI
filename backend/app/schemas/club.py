from datetime import datetime

from pydantic import BaseModel, Field


class ClubCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    description: str | None = Field(default=None, max_length=1000)
    coordinator_user_id: str | None = None


class ClubOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    coordinator_user_id: str | None = None
    is_active: bool = True
    created_at: datetime | None = None
