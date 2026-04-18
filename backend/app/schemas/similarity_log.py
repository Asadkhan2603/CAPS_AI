from datetime import datetime

from pydantic import BaseModel, Field


class SimilarityLogOut(BaseModel):
    id: str
    source_submission_id: str
    matched_submission_id: str
    source_submission_public_id: str | None = None
    matched_submission_public_id: str | None = None
    source_assignment_id: str | None = None
    matched_assignment_id: str | None = None
    source_assignment_label: str | None = None
    matched_assignment_label: str | None = None
    source_submission_summary: dict | None = None
    matched_submission_summary: dict | None = None
    source_class_id: str | None = None
    matched_class_id: str | None = None
    visible_to_extensions: list[str] = Field(default_factory=list)
    score: float = Field(ge=0, le=1)
    threshold: float = Field(ge=0, le=1)
    is_flagged: bool = False
    evidence_excerpts: list[dict] = Field(default_factory=list)
    overlap_stats: dict | None = None
    extraction_quality: dict | None = None
    extraction_diagnostics: dict | None = None
    semantic_shadow_score: float | None = Field(default=None, ge=0, le=1)
    decision_mode: str | None = None
    suppression_reason: str | None = None
    risk_signals: dict | None = None
    tokenization_mode_applied: str | None = None
    semantic_review_candidate: bool = False
    match_scope: str | None = None
    language_profile: dict | None = None
    candidate_count: int | None = None
    cap_reached: bool = False
    review_status: str | None = None
    review_reason_code: str | None = None
    review_notes: str | None = None
    reviewed_by_user_id: str | None = None
    reviewed_at: datetime | None = None
    review_updated_at: datetime | None = None
    review_finalized_at: datetime | None = None
    review_finalized_by_user_id: str | None = None
    counts_toward_calibration: bool = False
    calibration_eligible: bool = False
    language_bucket: str | None = None
    engine_version: str | None = None
    created_at: datetime | None = None
    schema_version: int = 1
    related_shadow_candidates: list[dict] = Field(default_factory=list)


class SimilarityRunQueuedResponse(BaseModel):
    success: bool = True
    status: str
    queued: bool
    submission_id: str
    candidate_count: int = Field(ge=0)
    async_only_threshold: int = Field(ge=1)
    detail: str
    job: dict
