import contextvars
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

# Context variable for request correlation ID
request_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar(
    "request_id", default="system"
)


def get_request_id() -> str:
    """Get current request correlation ID."""
    return request_id_ctx.get()


def set_request_id(req_id: str) -> None:
    """Set current request correlation ID."""
    request_id_ctx.set(req_id)


SENSITIVE_KEYS = {
    "password",
    "secret",
    "token",
    "authorization",
    "cookie",
    "api_key",
    "access_token",
    "refresh_token",
    "database_url",
}


def sanitize_data(data: Any) -> Any:
    """Recursively redact sensitive keys from dictionary data."""
    if isinstance(data, dict):
        clean_dict: dict[str, Any] = {}
        for k, v in data.items():
            if any(s in k.lower() for s in SENSITIVE_KEYS):
                clean_dict[k] = "[REDACTED]"
            else:
                clean_dict[k] = sanitize_data(v)
        return clean_dict
    if isinstance(data, list):
        return [sanitize_data(item) for item in data]
    return data


class RequestIDFilter(logging.Filter):
    """Injects current request ID and environment into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id()
        record.environment = settings.ENVIRONMENT
        return True


class JSONLogFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", "system"),
            "environment": getattr(record, "environment", settings.ENVIRONMENT),
        }
        if record.exc_info and record.exc_text:
            log_payload["exception"] = record.exc_text
        elif record.exc_info:
            log_payload["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_payload)


class TextLogFormatter(logging.Formatter):
    """Readable log formatter for local development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        req_id = getattr(record, "request_id", "system")
        msg = record.getMessage()
        base = f"{timestamp} [{record.levelname:<5}] [req:{req_id}] [{record.name}]: {msg}"
        if record.exc_info:
            base += "\n" + self.formatException(record.exc_info)
        return base


def configure_logging() -> None:
    """Configure centralized logging for the backend application."""
    root_logger = logging.getLogger()
    root_logger.setLevel(settings.LOG_LEVEL.upper())

    # Remove existing handlers to avoid duplicates
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.addFilter(RequestIDFilter())

    if settings.LOG_FORMAT == "json":
        console_handler.setFormatter(JSONLogFormatter())
    else:
        console_handler.setFormatter(TextLogFormatter())

    root_logger.addHandler(console_handler)

    # Set appropriate levels for third-party chatty loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DB_ECHO else logging.WARNING
    )


logger = logging.getLogger("nexora")

