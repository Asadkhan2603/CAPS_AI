from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse


ENVELOPE_KEYS = {"success", "data", "error", "trace_id"}


def is_enveloped_payload(payload: Any) -> bool:
    return isinstance(payload, dict) and ENVELOPE_KEYS.issubset(set(payload.keys()))


def success_envelope(data: Any, trace_id: str | None) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "error": None,
        "trace_id": trace_id or "",
    }


def error_envelope(
    *,
    message: str,
    trace_id: str | None,
    error_id: str | None = None,
    detail: Any = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "data": None,
        "error": {
            "message": message,
            "error_id": error_id,
            "detail": detail,
        },
        "trace_id": trace_id or "",
        # Keep legacy fields for backward compatibility.
        "detail": detail if detail is not None else message,
        "error_id": error_id,
    }


def envelope_json_response(
    *,
    data: Any = None,
    trace_id: str | None = None,
    status_code: int = 200,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=success_envelope(data=data, trace_id=trace_id),
        headers=headers,
    )
