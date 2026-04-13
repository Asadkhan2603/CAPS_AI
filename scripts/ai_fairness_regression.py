from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
ARTIFACT_PATH = ROOT / "artifacts" / "ai_fairness_regression_report.json"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.fairness_regression import run_fairness_regression_suite  # noqa: E402


def _as_bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def main() -> int:
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        **run_fairness_regression_suite(),
    }
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    if _as_bool_env("AI_FAIRNESS_REGRESSION_ENFORCE_THRESHOLDS", True) and not bool(report["gates"]["passed"]):
        print("Fairness regression gate failed:", file=sys.stderr)
        for failure in report["gates"]["failures"]:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
