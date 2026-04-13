from __future__ import annotations

import asyncio
import json
import logging
import os
import statistics
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from bson import ObjectId
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
ARTIFACT_PATH = ROOT / "artifacts" / "ai_similarity_benchmark_report.json"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SKIP_STARTUP_TASKS", "1")

from app.core.ai_capacity import SIMILARITY_CANDIDATE_CAP, build_ai_capacity_baseline  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.main import app  # noqa: E402
from app.services.similarity_engine import build_similarity_retrieval_artifact  # noqa: E402
from app.services.similarity_pipeline import run_similarity_pipeline  # noqa: E402
from app.services.similarity_rollout import build_similarity_rollout_plan  # noqa: E402
from tests.test_auth import _setup_fake_db  # noqa: E402
from tests.test_main_missing_blocks import _admin_headers, _student_headers  # noqa: E402


def percentile(values: list[float], target: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * target)))
    return ordered[index]


def timed_run(label: str, iterations: int, func: Callable[[], None]) -> dict[str, float | str]:
    samples_ms: list[float] = []
    for _ in range(iterations):
        started = time.perf_counter()
        func()
        samples_ms.append((time.perf_counter() - started) * 1000)
    return {
        "label": label,
        "iterations": iterations,
        "avg_ms": round(statistics.mean(samples_ms), 2),
        "p95_ms": round(percentile(samples_ms, 0.95), 2),
        "max_ms": round(max(samples_ms), 2),
    }


def _assert_ok(response, *, expected_status: int = 200) -> None:
    assert response.status_code == expected_status, response.text


def _assert_similarity_handoff(response, *, expected_min_candidates: int) -> None:
    assert response.status_code in {200, 202}, response.text
    payload = response.json()
    if response.status_code == 202:
        assert payload.get("status") == "queued"
        assert int(payload.get("candidate_count") or 0) >= expected_min_candidates
        return
    assert isinstance(payload, list)


def _as_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def evaluate_benchmark_gates(
    metrics: list[dict[str, float | str]],
    *,
    max_sync_handoff_ms: float,
    max_background_processing_ms: float,
) -> dict[str, object]:
    metrics_by_label = {str(metric["label"]): metric for metric in metrics}
    failures: list[str] = []
    sync_handoff = metrics_by_label.get("similarity_sync_handoff") or {}
    background_processing = metrics_by_label.get("similarity_background_processing") or {}
    if float(sync_handoff.get("max_ms") or 0.0) > max_sync_handoff_ms:
        failures.append(
            f"similarity_sync_handoff max_ms {sync_handoff.get('max_ms')} exceeded {round(max_sync_handoff_ms, 2)} ms"
        )
    if float(background_processing.get("max_ms") or 0.0) > max_background_processing_ms:
        failures.append(
            "similarity_background_processing max_ms "
            f"{background_processing.get('max_ms')} exceeded {round(max_background_processing_ms, 2)} ms"
        )
    return {
        "passed": not failures,
        "thresholds": {
            "max_sync_handoff_ms": round(max_sync_handoff_ms, 2),
            "max_background_processing_ms": round(max_background_processing_ms, 2),
        },
        "failures": failures,
    }


def _seed_similarity_candidates(fake_db, *, assignment_id: str, count: int) -> None:
    now = datetime.now(timezone.utc)
    shared_text = (
        "Neural network optimization requires careful gradient tracking, regularization, "
        "and evaluation against held-out validation data."
    )
    for index in range(count):
        if index % 37 == 0:
            extracted_text = (
                "Neural network optimization requires careful gradient tracking, regularization, "
                f"and evaluation against held-out validation data variant {index}."
            )
        elif index % 11 == 0:
            extracted_text = (
                "Validation data and regularization are important when tuning deep learning systems "
                f"for reliable optimization round {index}."
            )
        else:
            extracted_text = (
                f"Candidate {index} discusses assignments, reflections, and unrelated coursework content {index}. "
                "This text should remain lower in lexical similarity."
            )
        fake_db.submissions.items.append(
            {
                "_id": ObjectId(),
                "assignment_id": assignment_id,
                "student_user_id": f"bench-student-{index}",
                "original_filename": f"bench-{index}.txt",
                "stored_filename": f"bench-{index}.txt",
                "content_type": "text/plain",
                "file_size_bytes": len(extracted_text.encode("utf-8")),
                "notes": None,
                "extracted_text": extracted_text,
                "similarity_score": None,
                "similarity_retrieval_artifact": build_similarity_retrieval_artifact(extracted_text),
                "ai_status": "pending",
                "created_at": now,
                "updated_at": now,
                "schema_version": 1,
            }
        )


def main() -> int:
    fake_db = _setup_fake_db()
    logging.getLogger("caps_api").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)

    benchmark_candidate_count = int(os.getenv("AI_SIMILARITY_BENCHMARK_CANDIDATES", str(SIMILARITY_CANDIDATE_CAP + 5)))
    preview_iterations = int(os.getenv("AI_SIMILARITY_BENCHMARK_PREVIEW_ITERATIONS", "1"))
    similarity_iterations = int(os.getenv("AI_SIMILARITY_BENCHMARK_SIMILARITY_ITERATIONS", "1"))
    detail_iterations = int(os.getenv("AI_SIMILARITY_BENCHMARK_DETAIL_ITERATIONS", "5"))
    max_sync_handoff_ms = float(os.getenv("AI_SIMILARITY_BENCHMARK_MAX_SYNC_HANDOFF_MS", "250"))
    max_background_processing_ms = float(
        os.getenv("AI_SIMILARITY_BENCHMARK_MAX_BACKGROUND_PROCESSING_MS", "20000")
    )
    enforce_thresholds = _as_bool_env("AI_SIMILARITY_BENCHMARK_ENFORCE_THRESHOLDS", True)

    with TestClient(app) as client:
        admin_headers = _admin_headers(client, "admin_similarity_benchmark@example.com")
        student_headers = _student_headers(client, "student_similarity_benchmark@example.com")

        assignment = client.post(
            "/api/v1/assignments/",
            json={
                "title": "AI Similarity Benchmark Assignment",
                "description": "Measure lexical review load and semantic shadow capture.",
                "total_marks": 100,
            },
            headers=admin_headers,
        )
        _assert_ok(assignment, expected_status=201)
        assignment_id = assignment.json()["id"]

        source_submission = client.post(
            "/api/v1/submissions/upload",
            data={"assignment_id": assignment_id},
            files={
                "file": (
                    "source.txt",
                    (
                        b"Neural network optimization requires careful gradient tracking, "
                        b"regularization, and evaluation against held-out validation data."
                    ),
                    "text/plain",
                )
            },
            headers=student_headers,
        )
        _assert_ok(source_submission, expected_status=201)
        submission_id = source_submission.json()["id"]

        _seed_similarity_candidates(fake_db, assignment_id=assignment_id, count=max(1, benchmark_candidate_count))

        evaluation_preview_metric = timed_run(
            "evaluation_preview",
            preview_iterations,
            lambda: _assert_ok(
                client.post(
                    "/api/v1/evaluations/ai-preview",
                    json={
                        "submission_id": submission_id,
                        "attendance_percent": 91,
                        "skill": 2.0,
                        "behavior": 2.0,
                        "report": 8,
                        "viva": 16,
                        "final_exam": 48,
                        "remarks": "Benchmark preview",
                    },
                    headers=admin_headers,
                )
            ),
        )

        similarity_handoff_metric = timed_run(
            "similarity_sync_handoff",
            similarity_iterations,
            lambda: _assert_similarity_handoff(
                client.post(
                    f"/api/v1/similarity/checks/run/{submission_id}?threshold=0.8",
                    headers=admin_headers,
                ),
                expected_min_candidates=max(1, int(settings.similarity_sync_inline_candidate_limit)),
            ),
        )

        source_doc = next(item for item in fake_db.submissions.items if str(item.get("_id")) == submission_id)
        source_assignment = next(
            item for item in fake_db.assignments.items if str(item.get("_id")) == assignment_id
        )
        similarity_processing_metric = timed_run(
            "similarity_background_processing",
            1,
            lambda: asyncio.run(
                run_similarity_pipeline(
                    submission_id=submission_id,
                    source=source_doc,
                    source_assignment=source_assignment,
                    active_threshold=0.8,
                    actor_user_id="benchmark-admin",
                )
            ),
        )
        similarity_items = [
            {
                "id": str(item["_id"]),
                "is_flagged": bool(item.get("is_flagged")),
            }
            for item in fake_db.similarity_logs.items
            if item.get("source_submission_id") == submission_id
        ]
        flagged_log = next((item for item in similarity_items if item.get("is_flagged")), similarity_items[0])
        log_id = flagged_log["id"]

        review_detail_metric = timed_run(
            "review_modal_detail",
            detail_iterations,
            lambda: _assert_ok(
                client.get(f"/api/v1/similarity/checks/{log_id}", headers=admin_headers)
            ),
        )

    baseline = build_ai_capacity_baseline()
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "provider_mode": baseline["provider_mode"],
        "openai_configured": bool(settings.openai_api_key),
        "benchmark_inputs": {
            "candidate_seed_count": benchmark_candidate_count,
            "candidate_cap": SIMILARITY_CANDIDATE_CAP,
            "preview_iterations": preview_iterations,
            "similarity_iterations": similarity_iterations,
            "detail_iterations": detail_iterations,
        },
        "rollout_plan": build_similarity_rollout_plan(),
        "metrics": [
            evaluation_preview_metric,
            similarity_handoff_metric,
            similarity_processing_metric,
            review_detail_metric,
        ],
        "gates": evaluate_benchmark_gates(
            [
                evaluation_preview_metric,
                similarity_handoff_metric,
                similarity_processing_metric,
                review_detail_metric,
            ],
            max_sync_handoff_ms=max_sync_handoff_ms,
            max_background_processing_ms=max_background_processing_ms,
        ),
        "notes": [
            "Evaluation preview latency uses the current provider mode; fallback-only environments will under-report production provider latency.",
            "Similarity benchmark seeds retrieval artifacts for a candidate set larger than the inline sync limit to exercise async handoff plus background similarity processing.",
            "Review-modal load is approximated by repeated GET /similarity/checks/{id} calls against the in-process backend.",
        ],
    }

    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if enforce_thresholds and not bool(report["gates"]["passed"]):
        print("Benchmark gate failed:", file=sys.stderr)
        for failure in report["gates"]["failures"]:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
