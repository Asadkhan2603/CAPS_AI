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
    evidence_excerpts: list[dict] = Field(default_factory=list)
    overlap_stats: dict | None = None
    extraction_quality: dict | None = None
    semantic_shadow_score: float | None = Field(default=None, ge=0, le=1)
    candidate_count: int | None = None
    cap_reached: bool = False
    review_status: str | None = None
    review_notes: str | None = None
    reviewed_by_user_id: str | None = None
    reviewed_at: datetime | None = None
    engine_version: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1


class SimilarityRunQueuedResponse(BaseModel):
    success: bool = True
    status: str
    queued: bool
    submission_id: str
    candidate_count: int = Field(ge=0)
    async_only_threshold: int = Field(ge=1)
    detail: str
    job: dict
