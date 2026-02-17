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
    evaluation_id: str
    requested_by_user_id: str
    reason: str
    status: ReviewTicketStatus = "pending"
    resolved_by_user_id: str | None = None
    resolved_at: datetime | None = None
    created_at: datetime | None = None
