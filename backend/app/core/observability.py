import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from uuid import uuid4


request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("request_id", default="")
trace_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("trace_id", default="")


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_error_id() -> str:
    return f"err_{uuid4().hex[:12]}"


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": _utc_now_iso(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_ctx.get() or None,
            "trace_id": trace_id_ctx.get() or None,
        }
        if isinstance(record.msg, dict):
            payload.update(record.msg)
            payload["message"] = record.msg.get("event", payload["message"])
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=True)


def setup_logging(level: str = "INFO") -> None:
    root_logger = logging.getLogger()
    root_logger.setLevel(level.upper())

    # Prevent duplicate handlers when app reloads in development.
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    stream = logging.StreamHandler(sys.stdout)
    stream.setFormatter(JsonFormatter())
    root_logger.addHandler(stream)
