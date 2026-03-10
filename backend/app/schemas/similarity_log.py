from datetime import datetime

from pydantic import BaseModel, Field


class SimilarityLogOut(BaseModel):
    id: str
    source_submission_id: str
    matched_submission_id: str
    source_assignment_id: str | None = None
    matched_assignment_id: str | None = None
    source_class_id: str | None = None
    matched_class_id: str | None = None
    visible_to_extensions: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)
    is_flagged: bool = False
    engine_version: str | None = None
    created_at: datetime | None = None
