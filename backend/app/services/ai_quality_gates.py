from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.services.false_positive_negative_regression import run_false_positive_negative_regression_suite
from app.services.fairness_regression import run_fairness_regression_suite
from app.services.semantic_shadow_calibration import run_semantic_shadow_calibration


_REPO_ROOT = Path(__file__).resolve().parents[3]
_ARTIFACT_DIR = _REPO_ROOT / "artifacts"
_BENCHMARK_ARTIFACT = _ARTIFACT_DIR / "ai_similarity_benchmark_report.json"
_SEMANTIC_ARTIFACT = _ARTIFACT_DIR / "ai_semantic_shadow_calibration_report.json"
_FAIRNESS_ARTIFACT = _ARTIFACT_DIR / "ai_fairness_regression_report.json"
_FALSE_POSITIVE_NEGATIVE_ARTIFACT = _ARTIFACT_DIR / "ai_false_positive_negative_regression_report.json"


def _load_artifact(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None


def _semantic_calibration_snapshot() -> dict[str, Any]:
    artifact_payload = _load_artifact(_SEMANTIC_ARTIFACT)
    artifact = artifact_payload or run_semantic_shadow_calibration()
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    recommendations = artifact.get("recommendations") if isinstance(artifact.get("recommendations"), dict) else {}
    gates = artifact.get("gates") if isinstance(artifact.get("gates"), dict) else {}
    return {
        "status": "passed" if bool(gates.get("passed")) else "failed",
        "generated_at": artifact.get("generated_at"),
        "source": "artifact" if artifact_payload else "live",
        "case_count": int(summary.get("case_count") or 0),
        "failed_count": int(summary.get("failed_count") or 0),
        "recommended_semantic_advantage_trigger": recommendations.get("recommended_semantic_advantage_trigger"),
        "failures": gates.get("failures") or [],
    }


def _fairness_regression_snapshot() -> dict[str, Any]:
    artifact_payload = _load_artifact(_FAIRNESS_ARTIFACT)
    artifact = artifact_payload or run_fairness_regression_suite()
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    gates = artifact.get("gates") if isinstance(artifact.get("gates"), dict) else {}
    thresholds = artifact.get("thresholds") if isinstance(artifact.get("thresholds"), dict) else {}
    coverage = artifact.get("coverage") if isinstance(artifact.get("coverage"), dict) else {}
    return {
        "status": "passed" if bool(gates.get("passed")) else "failed",
        "generated_at": artifact.get("generated_at"),
        "source": "artifact" if artifact_payload else "live",
        "check_count": int(summary.get("check_count") or 0),
        "failed_count": int(summary.get("failed_count") or 0),
        "max_observed_delta": summary.get("max_observed_delta"),
        "thresholds": thresholds,
        "coverage": coverage,
        "failures": gates.get("failures") or [],
    }


def _benchmark_snapshot() -> dict[str, Any]:
    artifact = _load_artifact(_BENCHMARK_ARTIFACT)
    if not artifact:
        return {
            "status": "missing",
            "generated_at": None,
            "source": "missing",
            "metrics": {},
            "failures": ["Benchmark artifact not found. Run scripts/ai_similarity_benchmark.py to refresh the snapshot."],
        }

    gates = artifact.get("gates") if isinstance(artifact.get("gates"), dict) else {}
    metrics = artifact.get("metrics") if isinstance(artifact.get("metrics"), list) else []
    metrics_by_label = {
        str(item.get("label")): item
        for item in metrics
        if isinstance(item, dict) and item.get("label")
    }
    return {
        "status": "passed" if bool(gates.get("passed")) else "failed",
        "generated_at": artifact.get("generated_at"),
        "source": "artifact",
        "metrics": {
            "sync_handoff_ms": (metrics_by_label.get("similarity_sync_handoff") or {}).get("avg_ms"),
            "background_processing_ms": (metrics_by_label.get("similarity_background_processing") or {}).get("avg_ms"),
            "review_modal_detail_ms": (metrics_by_label.get("review_modal_detail") or {}).get("avg_ms"),
        },
        "thresholds": gates.get("thresholds") or {},
        "failures": gates.get("failures") or [],
    }


def _false_positive_negative_regression_snapshot() -> dict[str, Any]:
    artifact_payload = _load_artifact(_FALSE_POSITIVE_NEGATIVE_ARTIFACT)
    artifact = artifact_payload or run_false_positive_negative_regression_suite()
    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    gates = artifact.get("gates") if isinstance(artifact.get("gates"), dict) else {}
    thresholds = artifact.get("thresholds") if isinstance(artifact.get("thresholds"), dict) else {}
    coverage = artifact.get("coverage") if isinstance(artifact.get("coverage"), dict) else {}
    return {
        "status": "passed" if bool(gates.get("passed")) else "failed",
        "generated_at": artifact.get("generated_at"),
        "source": "artifact" if artifact_payload else "live",
        "case_count": int(summary.get("case_count") or 0),
        "failed_count": int(summary.get("failed_count") or 0),
        "flagged_count": int(summary.get("flagged_count") or 0),
        "assist_only_count": int(summary.get("assist_only_count") or 0),
        "suppressed_count": int(summary.get("suppressed_count") or 0),
        "thresholds": thresholds,
        "coverage": coverage,
        "failures": gates.get("failures") or [],
    }


def build_ai_quality_gate_snapshot() -> dict[str, Any]:
    return {
        "semantic_calibration": _semantic_calibration_snapshot(),
        "fairness_regression": _fairness_regression_snapshot(),
        "false_positive_negative_regression": _false_positive_negative_regression_snapshot(),
        "benchmark": _benchmark_snapshot(),
    }
