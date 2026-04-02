from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

ReviewTicketStatus = Literal["pending", "approved", "rejected"]


class ReviewTicketCreate(BaseModel):
    evaluation_id: str = Field(min_length=1)
    reason: str = Field(min_length=5, max_length=1000)


class ReviewTicketDecision(BaseModel):
    reason: str | None = Field(default=None, max_length=1000)


class ReviewTicketOut(BaseModel):
    id: str
    public_id: str | None = None
    display_label: str | None = None
    evaluation_id: str
    evaluation_label: str | None = None
    requested_by_user_id: str
    requested_by_label: str | None = None
    reason: str
    status: ReviewTicketStatus = "pending"
    resolved_by_user_id: str | None = None
    resolved_by_label: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None
    schema_version: int = 1
