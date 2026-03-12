from __future__ import annotations

from typing import Any

SUBMISSION_SCHEMA_VERSION = 1
EVALUATION_SCHEMA_VERSION = 1


def normalize_schema_version(raw_value: Any, *, default: int) -> int:
    try:
        parsed = int(raw_value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 1 else default
