"""Central logging configuration (structured, stdout-based)."""

from __future__ import annotations

import logging
import sys

DEFAULT_FORMAT = "%(asctime)s %(levelname)-8s %(name)s :: %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: int = logging.INFO, fmt: str = DEFAULT_FORMAT) -> None:
    """Reset the root logger to a single, deterministic stdout handler."""
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=fmt, datefmt=DEFAULT_DATE_FORMAT))
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    """Return a child logger of the given name."""
    return logging.getLogger(name)
