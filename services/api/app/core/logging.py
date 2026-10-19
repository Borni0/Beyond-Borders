"""Structured logging configuration (sensitive values are redacted)."""

from __future__ import annotations

import logging
import sys

import structlog

from app.core.config import settings

# Fields that must never be logged in plain form.
REDACT_KEYS = {
    "password",
    "token",
    "session",
    "cookie",
    "authorization",
    "secret",
    "reset_token",
}


def _redact(_, __, event_dict):  # type: ignore[no-untyped-def]
    for key in list(event_dict.keys()):
        if any(r in key.lower() for r in REDACT_KEYS):
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging() -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level, logging.INFO),
    )
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            _redact,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, settings.log_level, logging.INFO)
        ),
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    return structlog.get_logger(name)