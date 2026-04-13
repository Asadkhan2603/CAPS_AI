from __future__ import annotations

import math
from typing import Any

from app.core.config import settings
from app.services.ai_runtime import AI_SIMILARITY_ENGINE_VERSION
from app.services.similarity_rollout import build_similarity_rollout_plan

AI_JOB_MAX_JOBS_PER_TICK = 3
SIMILARITY_CANDIDATE_CAP = 1000
SIMILARITY_WARNING_CANDIDATE_COUNT = 800
AI_QUEUE_WARNING_AGE_SECONDS = 120
AI_QUEUE_CRITICAL_AGE_SECONDS = 300
AI_FALLBACK_WARNING_RATE_PCT = 25.0
AI_FALLBACK_CRITICAL_RATE_PCT = 50.0


def build_ai_capacity_baseline() -> dict[str, Any]:
    ai_job_poll_seconds = max(5, int(settings.ai_job_poll_seconds))
    pickup_ceiling_per_minute = round((60 / ai_job_poll_seconds) * AI_JOB_MAX_JOBS_PER_TICK, 2)
    pickup_ceiling_per_15m = round(pickup_ceiling_per_minute * 15, 2)
    queue_warn_depth = math.ceil(pickup_ceiling_per_minute * 2)
    queue_critical_depth = math.ceil(pickup_ceiling_per_minute * 5)
    rollout_plan = build_similarity_rollout_plan()

    return {
        "provider_mode": "openai+fallback" if bool(settings.openai_api_key) else "fallback-only",
        "openai_model": settings.openai_model,
        "openai_timeout_seconds": int(settings.openai_timeout_seconds),
        "openai_max_output_tokens": int(settings.openai_max_output_tokens),
        "similarity_threshold": float(settings.similarity_threshold),
        "similarity_engine_version": AI_SIMILARITY_ENGINE_VERSION,
        "scheduler": {
            "enabled": bool(settings.scheduler_enabled),
            "single_leader": True,
            "lock_ttl_seconds": int(settings.scheduler_lock_ttl_seconds),
            "lock_renew_seconds": int(settings.scheduler_lock_renew_seconds),
            "ai_job_poll_seconds": ai_job_poll_seconds,
            "ai_job_max_jobs_per_tick": AI_JOB_MAX_JOBS_PER_TICK,
            "pickup_ceiling_jobs_per_minute": pickup_ceiling_per_minute,
            "pickup_ceiling_jobs_per_15m": pickup_ceiling_per_15m,
            "queue_warn_depth": queue_warn_depth,
            "queue_critical_depth": queue_critical_depth,
            "queue_warn_age_seconds": AI_QUEUE_WARNING_AGE_SECONDS,
            "queue_critical_age_seconds": AI_QUEUE_CRITICAL_AGE_SECONDS,
        },
        "similarity": {
            "candidate_cap_per_run": SIMILARITY_CANDIDATE_CAP,
            "candidate_warn_threshold": SIMILARITY_WARNING_CANDIDATE_COUNT,
            "sync_inline_candidate_limit": max(1, int(settings.similarity_sync_inline_candidate_limit)),
            "retrieval_cache_enabled": bool(settings.similarity_retrieval_cache_enabled),
            "retrieval_terms_limit": max(8, int(settings.similarity_retrieval_terms_limit)),
            "prefilter_enabled": bool(settings.similarity_prefilter_enabled),
            "prefilter_top_k": max(1, int(settings.similarity_prefilter_top_k)),
            "prefilter_min_shared_tokens": max(0, int(settings.similarity_prefilter_min_shared_tokens)),
            "processing_model": "assignment-scoped cached retrieval shortlist plus tfidf lexical similarity with shadow semantic scoring in app worker",
            "semantic_shadow": rollout_plan["semantic_shadow"],
            "multilingual_plan": rollout_plan["multilingual"],
            "fairness_regression": rollout_plan["fairness_regression"],
        },
        "fallback": {
            "warning_rate_pct": AI_FALLBACK_WARNING_RATE_PCT,
            "critical_rate_pct": AI_FALLBACK_CRITICAL_RATE_PCT,
        },
        "capacity_notes": [
            "Queue pickup ceiling assumes jobs finish faster than the poll interval. Slow jobs reduce actual throughput.",
            "Similarity runs are bounded by assignment-local candidate selection and currently cap at 1000 submissions per run.",
            "Assignment-level retrieval now uses cached per-submission token artifacts before full-text TF-IDF scoring.",
            "Inline similarity runs above the sync candidate limit are automatically deferred to the durable job queue.",
            "Bulk submission AI jobs can contain multiple submissions, so queue depth alone does not represent token or CPU cost.",
            "Scheduler leadership failover is bounded by the lock TTL if the active leader dies without releasing the lock.",
        ],
    }
