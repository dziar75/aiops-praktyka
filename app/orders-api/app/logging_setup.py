"""Structured JSON logging to stdout."""
from __future__ import annotations

import json
import logging
import sys
import traceback
from datetime import datetime, timezone
from typing import Any

from .config import settings

try:
    from opentelemetry import trace as _trace
except Exception:  # pragma: no cover - otel optional
    _trace = None  # type: ignore[assignment]

_RESERVED = set(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}

# Extra fields that are promoted to top level when supplied via `extra=`.
_PROMOTED = ("service", "route", "status", "duration_ms", "order_id", "employee_id")


def _current_trace_ids() -> tuple[str | None, str | None]:
    if _trace is None:
        return None, None
    span = _trace.get_current_span()
    ctx = span.get_span_context()
    if not ctx or not ctx.is_valid:
        return None, None
    return format(ctx.trace_id, "032x"), format(ctx.span_id, "016x")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        trace_id, span_id = _current_trace_ids()
        payload: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.getMessage(),
            "service": settings.service_name,
            "version": settings.version,
            "trace_id": trace_id,
            "span_id": span_id,
        }

        for key in _PROMOTED:
            if key in record.__dict__ and record.__dict__[key] is not None:
                payload[key] = record.__dict__[key]

        # Any remaining non-reserved extras.
        for key, value in record.__dict__.items():
            if key in _RESERVED or key in payload or key in _PROMOTED:
                continue
            payload[key] = value

        if record.exc_info:
            payload["exc_info"] = "".join(traceback.format_exception(*record.exc_info)).strip()
        elif record.exc_text:
            payload["exc_info"] = record.exc_text

        return json.dumps(payload, default=str, ensure_ascii=False)


def configure_logging() -> None:
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    for handler in list(root.handlers):
        root.removeHandler(handler)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.addHandler(handler)

    # Route uvicorn logs through the same JSON handler.
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        lg = logging.getLogger(name)
        lg.handlers = []
        lg.propagate = True
    logging.getLogger("uvicorn.access").disabled = True
