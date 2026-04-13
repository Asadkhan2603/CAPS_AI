from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = ROOT / "backend"
ARTIFACT_PATH = ROOT / "artifacts" / "ai_reviewer_outcome_calibration_report.json"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

os.environ.setdefault("SKIP_STARTUP_TASKS", "1")

from app.core.database import db  # noqa: E402
from app.services.reviewer_outcome_calibration import build_reviewer_outcome_calibration_report  # noqa: E402


async def _main() -> int:
    report = await build_reviewer_outcome_calibration_report(database=db)
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(_main()))
