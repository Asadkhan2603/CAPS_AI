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
    semantic_shadow = similarity["semantic_shadow"]
    multilingual_plan = similarity["multilingual_plan"]
    fairness_regression = similarity["fairness_regression"]
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
        f"- Sync inline candidate limit: `{similarity['sync_inline_candidate_limit']}` submissions",
        f"- Retrieval cache enabled: `{similarity['retrieval_cache_enabled']}`",
        f"- Retrieval terms limit: `{similarity['retrieval_terms_limit']}` tokens",
        f"- Prefilter enabled: `{similarity['prefilter_enabled']}`",
        f"- Prefilter top-K: `{similarity['prefilter_top_k']}` candidates",
        f"- Prefilter min shared tokens: `{similarity['prefilter_min_shared_tokens']}`",
        f"- Processing model: `{similarity['processing_model']}`",
        "",
        "## Semantic Shadow Pilot",
        "",
        f"- Enabled: `{semantic_shadow['enabled']}`",
        f"- Capture top-N lexical candidates: `{semantic_shadow['capture_top_n']}`",
        f"- Minimum lexical score for shadow capture: `{semantic_shadow['min_lexical_score']}`",
        f"- Cross-assignment enabled: `{semantic_shadow['cross_assignment_enabled']}`",
        f"- Flagging mode: `{semantic_shadow['flagging_mode']}`",
        "",
        "## Fairness Regression Gate",
        "",
        f"- Gate mode: `{fairness_regression['gate_mode']}`",
        f"- Max concise-vs-verbose delta: `{fairness_regression['max_concise_delta']}`",
        f"- Max formula-vs-prose delta: `{fairness_regression['max_formula_delta']}`",
        f"- Max mixed-language evaluation delta: `{fairness_regression['max_mixed_language_eval_delta']}`",
        "",
        "## Multilingual Rollout Plan",
        "",
        f"- Language detection enabled: `{multilingual_plan['language_detection_enabled']}`",
        f"- Detector: `{multilingual_plan['language_detector']}`",
        f"- Tokenizer mode: `{multilingual_plan['tokenizer_mode']}`",
        f"- Stopword strategy: `{multilingual_plan['stopword_strategy']}`",
        f"- Mixed-language mode: `{multilingual_plan['mixed_language_mode']}`",
        "",
        "## Notes",
        "",
    ]
    lines.extend([f"- {note}" for note in baseline["capacity_notes"]])
    lines.append("")
    lines.append("## Multilingual Notes")
    lines.append("")
    lines.extend([f"- {note}" for note in multilingual_plan["notes"]])
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
