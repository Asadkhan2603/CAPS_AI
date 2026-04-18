import asyncio

from fastapi.responses import JSONResponse, Response
from starlette.responses import StreamingResponse
from starlette.requests import Request

from app.main import (
    _can_wrap_response_body,
    _read_response_body,
    _should_skip_response_envelope,
    _wrap_response_payload,
)
from app.core.config import settings
from app.core.response import success_envelope


def _build_request(path: str) -> Request:
    scope = {
        "type": "http",
        "method": "GET",
        "path": path,
        "headers": [],
        "query_string": b"",
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "scheme": "http",
    }
    return Request(scope)


def test_should_skip_response_envelope_for_non_api_paths() -> None:
    request = _build_request("/health")
    response = JSONResponse({"status": "ok"})
    assert _should_skip_response_envelope(request, response) is True


def test_should_skip_response_envelope_for_error_and_skip_paths() -> None:
    original_enabled = settings.response_envelope_enabled
    original_skip_paths = list(settings.response_envelope_skip_paths)
    settings.response_envelope_enabled = True
    settings.response_envelope_skip_paths = ["/api/v1/auth/me"]
    try:
        skipped_request = _build_request("/api/v1/auth/me")
        skipped_response = JSONResponse({"email": "admin@example.com"})
        assert _should_skip_response_envelope(skipped_request, skipped_response) is True

        error_request = _build_request("/api/v1/auth/login")
        error_response = JSONResponse({"detail": "bad"}, status_code=400)
        assert _should_skip_response_envelope(error_request, error_response) is True
    finally:
        settings.response_envelope_enabled = original_enabled
        settings.response_envelope_skip_paths = original_skip_paths


def test_can_wrap_response_body_rejects_large_or_streaming_payloads() -> None:
    large_response = Response(
        content=b"x" * 8,
        media_type="application/json",
        headers={"content-length": str(2 * 1024 * 1024)},
    )
    assert _can_wrap_response_body(large_response) is False

    streaming_like = StreamingResponse(iter([b'{"chunked":true}']), media_type="application/json")
    assert _can_wrap_response_body(streaming_like) is False


def test_wrap_response_payload_preserves_existing_envelopes_and_wraps_plain_json() -> None:
    enveloped = success_envelope(data={"ok": True}, trace_id="trace-1")
    plain = {"message": "ok"}

    assert _wrap_response_payload(JSONResponse(enveloped).body) == enveloped
    wrapped_plain = _wrap_response_payload(JSONResponse(plain).body)
    assert wrapped_plain["success"] is True
    assert wrapped_plain["data"] == plain


def test_read_response_body_returns_json_response_bytes() -> None:
    response = JSONResponse({"hello": "world"})
    body = asyncio.run(_read_response_body(response))
    assert body == response.body
