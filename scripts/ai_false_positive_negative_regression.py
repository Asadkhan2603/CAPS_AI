from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
ARTIFACT_PATH = ROOT / "artifacts" / "ai_false_positive_negative_regression_report.json"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.false_positive_negative_regression import run_false_positive_negative_regression_suite  # noqa: E402


def main() -> int:
    report = run_false_positive_negative_regression_suite()
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report.get("gates", {}).get("passed") else 1


if __name__ == "__main__":
    raise SystemExit(main())
