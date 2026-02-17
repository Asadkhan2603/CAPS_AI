from datetime import datetime

from pydantic import BaseModel, Field


class SimilarityLogOut(BaseModel):
    id: str
    source_submission_id: str
    matched_submission_id: str
    score: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)
    is_flagged: bool = False
    created_at: datetime | None = None
