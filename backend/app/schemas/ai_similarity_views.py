from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class AISimilarityViewFilters(BaseModel):
    search: str = Field(default="", max_length=120)
    review_status: str = Field(default="", max_length=40)
    decision_mode: str = Field(default="", max_length=40)
    awaiting_final_decision: bool = False
    stale_review: bool = False
    counts_toward_calibration: bool = False
    calibration_eligible: bool = False
    semantic_review_candidate: bool = False
    semantic_drift_present: bool = False
    match_scope: str = Field(default="", max_length=64)
    language_bucket: str = Field(default="", max_length=64)
    cap_reached: bool = False
    low_extraction_quality: bool = False
    min_score: float | None = Field(default=None, ge=0, le=1)
    max_score: float | None = Field(default=None, ge=0, le=1)


class AISimilarityViewCreate(BaseModel):
    name: str = Field(min_length=2, max_length=60)
    filters: AISimilarityViewFilters


class AISimilarityViewOut(BaseModel):
    id: str
    library_key: str
    name: str
    filters: AISimilarityViewFilters
    created_by_user_id: str | None = None
    created_by_label: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    schema_version: int = 1
