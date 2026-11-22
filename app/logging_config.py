"""Sends all logs to stdout as one JSON object per line.

Rule: never log referral details (reference, practice). Log IDs and event names only.
"""
import json
import logging
import sys
from datetime import datetime, timezone

# Extra fields callers may attach with logger.info("event", extra={...}).
# Anything not on this list is dropped, so referral details can't slip in by accident.
ALLOWED_EXTRA_FIELDS = {
    "event", "referral_id", "old_status", "new_status", "priority",
    "method", "path", "status_code", "duration_ms", "count", "attempt", "error",
}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in ALLOWED_EXTRA_FIELDS:
            if key in record.__dict__:
                entry[key] = record.__dict__[key]
        if record.exc_info:
            # Exception type only: full tracebacks and messages can contain data values.
            entry["exception"] = record.exc_info[0].__name__ if record.exc_info[0] else None
        return json.dumps(entry)


def setup_logging(level: str) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    # Our own middleware logs each request, so silence uvicorn's plain-text access log.
    logging.getLogger("uvicorn.access").disabled = True
    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True
