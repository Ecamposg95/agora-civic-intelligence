"""Structured, environment-aware logging configuration."""

import logging
import sys

from app.core.config import settings

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def configure_logging() -> None:
    """Configure root logging once at application startup."""
    level = logging.INFO if settings.is_production else logging.DEBUG

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_LOG_FORMAT))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Tame noisy third-party loggers in production.
    logging.getLogger("uvicorn.access").setLevel(
        logging.WARNING if settings.is_production else logging.INFO
    )


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger."""
    return logging.getLogger(name)
