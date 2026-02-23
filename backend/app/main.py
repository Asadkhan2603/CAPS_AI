from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from uuid import uuid4
import logging
import time

from app.api.v1.router import api_router

from app.core.config import settings
from app.core.indexes import ensure_indexes
from app.core.observability import (
    new_error_id,
    request_id_ctx,
    setup_logging,
    trace_id_ctx,
)
from app.core.rate_limit import RateLimitMiddleware

setup_logging(settings.log_level)
logger = logging.getLogger("caps_api")

app = FastAPI(title=settings.app_name, version=settings.app_version)

app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_max_requests,
    window_seconds=settings.rate_limit_window_seconds,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid4())
        trace_id = request.headers.get("x-trace-id") or str(uuid4())
        request_id_token = request_id_ctx.set(request_id)
        trace_id_token = trace_id_ctx.set(trace_id)
        started = time.perf_counter()
        logger.info(
            {
                "event": "request.start",
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "query": str(request.url.query or ""),
                "client_ip": request.client.host if request.client else None,
            }
        )
        try:
            response: Response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - started) * 1000)
            logger.exception(
                {
                    "event": "request.unhandled_exception",
                    "request_id": request_id,
                    "trace_id": trace_id,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                }
            )
            raise
        duration_ms = int((time.perf_counter() - started) * 1000)

        response.headers["X-Request-Id"] = request_id
        response.headers["X-Trace-Id"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        logger.info(
            {
                "event": "request.end",
                "request_id": request_id,
                "trace_id": trace_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }
        )
        request_id_ctx.reset(request_id_token)
        trace_id_ctx.reset(trace_id_token)
        return response


app.add_middleware(SecurityHeadersMiddleware)

app.include_router(api_router, prefix=settings.api_prefix)


@app.on_event("startup")
async def startup_tasks() -> None:
    await ensure_indexes()


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    error_id = new_error_id()
    logger.warning(
        {
            "event": "http.error",
            "error_id": error_id,
            "request_id": request_id_ctx.get() or None,
            "trace_id": trace_id_ctx.get() or None,
            "status_code": exc.status_code,
            "method": request.method,
            "path": request.url.path,
            "detail": exc.detail,
        }
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={"success": False, "detail": exc.detail, "error_id": error_id},
        headers={"X-Error-Id": error_id},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    error_id = new_error_id()
    logger.warning(
        {
            "event": "http.validation_error",
            "error_id": error_id,
            "request_id": request_id_ctx.get() or None,
            "trace_id": trace_id_ctx.get() or None,
            "status_code": 422,
            "method": request.method,
            "path": request.url.path,
            "detail": exc.errors(),
        }
    )
    return JSONResponse(
        status_code=422,
        content={"success": False, "detail": exc.errors(), "error_id": error_id},
        headers={"X-Error-Id": error_id},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    error_id = new_error_id()
    logger.exception(
        {
            "event": "http.unhandled_error",
            "error_id": error_id,
            "request_id": request_id_ctx.get() or None,
            "trace_id": trace_id_ctx.get() or None,
            "status_code": 500,
            "method": request.method,
            "path": request.url.path,
        }
    )
    return JSONResponse(
        status_code=500,
        content={"success": False, "detail": "Internal server error", "error_id": error_id},
        headers={"X-Error-Id": error_id},
    )


@app.get("/health")
async def health_check() -> dict:
    return {"status": "ok"}


@app.get("/")
async def root() -> dict:
    return {"message": "CAPS AI API is running"}
