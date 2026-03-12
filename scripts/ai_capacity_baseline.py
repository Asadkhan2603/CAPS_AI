from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.ai_capacity import build_ai_capacity_baseline  # noqa: E402


def build_capacity_baseline() -> dict[str, object]:
    return build_ai_capacity_baseline()


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
