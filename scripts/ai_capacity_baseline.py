from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings  # noqa: E402
from app.services.ai_runtime import AI_SIMILARITY_ENGINE_VERSION  # noqa: E402

AI_JOB_MAX_JOBS_PER_TICK = 3
SIMILARITY_CANDIDATE_CAP = 1000
SIMILARITY_WARNING_CANDIDATE_COUNT = 800


def build_capacity_baseline() -> dict[str, object]:
    ai_job_poll_seconds = max(5, int(settings.ai_job_poll_seconds))
    pickup_ceiling_per_minute = round((60 / ai_job_poll_seconds) * AI_JOB_MAX_JOBS_PER_TICK, 2)
    pickup_ceiling_per_15m = round(pickup_ceiling_per_minute * 15, 2)
    queue_warn_depth = math.ceil(pickup_ceiling_per_minute * 2)
    queue_critical_depth = math.ceil(pickup_ceiling_per_minute * 5)

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
        },
        "similarity": {
            "candidate_cap_per_run": SIMILARITY_CANDIDATE_CAP,
            "candidate_warn_threshold": SIMILARITY_WARNING_CANDIDATE_COUNT,
            "processing_model": "single-process tfidf cosine similarity in app worker",
        },
        "capacity_notes": [
            "Queue pickup ceiling assumes jobs finish faster than the poll interval. Slow jobs reduce actual throughput.",
            "Similarity runs are bounded by assignment-local candidate selection and currently cap at 1000 submissions per run.",
            "Bulk submission AI jobs can contain multiple submissions, so queue depth alone does not represent token or CPU cost.",
            "Scheduler leadership failover is bounded by the lock TTL if the active leader dies without releasing the lock.",
        ],
    }


def emit_markdown(baseline: dict[str, object]) -> str:
    scheduler = baseline["scheduler"]
    similarity = baseline["similarity"]
    lines = [
        "# AI Capacity Baseline",
        "",
        f"- Provider mode: `{baseline['provider_mode']}`",
        f"- OpenAI model: `{baseline['openai_model']}`",
        f"- OpenAI timeout: `{baseline['openai_timeout_seconds']}s`",
        f"- OpenAI max output tokens: `{baseline['openai_max_output_tokens']}`",
        f"- Similarity threshold: `{baseline['similarity_threshold']}`",
        f"- Similarity engine: `{baseline['similarity_engine_version']}`",
        "",
        "## Scheduler And Queue",
        "",
        f"- Single leader scheduler: `{scheduler['single_leader']}`",
        f"- AI job poll interval: `{scheduler['ai_job_poll_seconds']}s`",
        f"- Max jobs picked per tick: `{scheduler['ai_job_max_jobs_per_tick']}`",
        f"- Queue pickup ceiling: `{scheduler['pickup_ceiling_jobs_per_minute']}` jobs/minute",
        f"- Queue pickup ceiling: `{scheduler['pickup_ceiling_jobs_per_15m']}` jobs/15m",
        f"- Queue warning depth: `{scheduler['queue_warn_depth']}` queued jobs",
        f"- Queue critical depth: `{scheduler['queue_critical_depth']}` queued jobs",
        f"- Scheduler failover upper bound: `{scheduler['lock_ttl_seconds']}s`",
        "",
        "## Similarity",
        "",
        f"- Candidate cap per run: `{similarity['candidate_cap_per_run']}` submissions",
        f"- Candidate warning threshold: `{similarity['candidate_warn_threshold']}` submissions",
        f"- Processing model: `{similarity['processing_model']}`",
        "",
        "## Notes",
        "",
    ]
    lines.extend([f"- {note}" for note in baseline["capacity_notes"]])
    return "\n".join(lines)


def main() -> int:
    baseline = build_capacity_baseline()
    if "--json" in sys.argv:
        print(json.dumps(baseline, indent=2))
    else:
        print(emit_markdown(baseline))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
