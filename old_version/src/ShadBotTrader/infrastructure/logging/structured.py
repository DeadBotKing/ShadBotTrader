"""Structured, contextual logging (Phase 22, §7-31).

Three requirements drive this module:

**Structured records (§7-9).** A log line is data, not prose. Every
record carries at minimum a timestamp, a level and a message, plus
whatever context is in scope — correlation id, run id, component. Text
logs cannot be filtered or correlated after the fact; JSON can.

**Context propagates (§15-21).** A correlation id set once at the top of
a trading cycle appears on every record that cycle produces, without
being threaded through forty function signatures. ``contextvars`` makes
this work correctly under threads, which is what the command bus and the
runner both use.

**Secrets never reach a sink (§20 of Phase 21).** Redaction happens
inside the logger. A rule enforced at one choke point cannot be
forgotten at a call site.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import threading
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Mapping, Optional

from ShadBotTrader.infrastructure.configuration.layered import REDACTED, is_secret_key

#: Ambient context merged into every record on this thread/task.
#:
#: The default is ``None`` rather than ``{}``: a mutable default on a
#: ContextVar is shared by every context that never set a value, so one
#: accidental in-place mutation would leak fields across unrelated
#: operations. Readers materialise a fresh dict instead.
_CONTEXT: ContextVar[Optional[Dict[str, Any]]] = ContextVar("shadbot_log_context", default=None)

#: Levels, in the order §4 defines them.
LEVELS = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")


def new_correlation_id() -> str:
    """A short id for one logical operation (§17)."""
    return uuid.uuid4().hex[:16]


def current_context() -> Dict[str, Any]:
    """The context in scope right now (always a fresh copy)."""
    return dict(_CONTEXT.get() or {})


@contextmanager
def log_context(**values: Any) -> Iterator[Dict[str, Any]]:
    """Add fields to every record emitted inside the block (§16).

    Nested blocks merge, and the previous context is always restored —
    including when the body raises, which is exactly when the context
    matters most.
    """
    previous = _CONTEXT.get() or {}
    merged = {**previous, **{key: value for key, value in values.items() if value is not None}}
    token = _CONTEXT.set(merged)
    try:
        yield merged
    finally:
        _CONTEXT.reset(token)


@contextmanager
def correlation_scope(correlation_id: Optional[str] = None) -> Iterator[str]:
    """Start a correlated operation, generating an id when none is given."""
    identifier = correlation_id or new_correlation_id()
    with log_context(correlation_id=identifier):
        yield identifier


def _redact_value(key: str, value: Any) -> Any:
    if isinstance(value, Mapping):
        return {inner: _redact_value(inner, item) for inner, item in value.items()}
    if is_secret_key(key) and value is not None:
        return REDACTED
    return value


@dataclass
class LogRecord:
    """One structured record (Phase 22, §8).

    Only ``timestamp``, ``level`` and ``message`` are mandatory (§9);
    everything else is included when it is actually known. Emitting
    empty fields makes every line noisier without adding information.
    """

    timestamp: str
    level: str
    message: str
    logger_name: str = ""
    event: str = ""
    component: str = ""
    environment: str = ""
    correlation_id: str = ""
    run_id: str = ""
    process_id: int = 0
    thread_name: str = ""
    module: str = ""
    function: str = ""
    line: int = 0
    exception: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "timestamp": self.timestamp,
            "level": self.level,
            "message": self.message,
        }
        optional = {
            "logger": self.logger_name,
            "event": self.event,
            "component": self.component,
            "environment": self.environment,
            "correlation_id": self.correlation_id,
            "run_id": self.run_id,
            "process_id": self.process_id,
            "thread": self.thread_name,
            "module": self.module,
            "function": self.function,
            "line": self.line,
            "exception": self.exception,
        }
        payload.update({key: value for key, value in optional.items() if value})
        if self.metadata:
            payload["metadata"] = self.metadata
        return payload

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), default=str, ensure_ascii=False)

    def to_text(self) -> str:
        """Human-readable form for a console."""
        parts = [self.timestamp[:23], f"{self.level:<8}"]
        if self.component:
            parts.append(f"[{self.component}]")
        if self.correlation_id:
            parts.append(f"({self.correlation_id[:8]})")
        parts.append(self.message)
        if self.metadata:
            extras = " ".join(f"{key}={value}" for key, value in self.metadata.items())
            parts.append(f"| {extras}")
        return " ".join(parts)


class JsonFormatter(logging.Formatter):
    """Renders any stdlib record as one JSON object (§12)."""

    def __init__(self, environment: str = "", service: str = "shadbottrader") -> None:
        super().__init__()
        self._environment = environment
        self._service = service

    def format(self, record: logging.LogRecord) -> str:
        return self._build(record).to_json()

    def _build(self, record: logging.LogRecord) -> LogRecord:
        context = current_context()
        metadata = dict(getattr(record, "metadata", {}) or {})
        for key, value in record.__dict__.items():
            if key.startswith("ctx_"):
                metadata[key[4:]] = value

        return LogRecord(
            timestamp=datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            level=record.levelname,
            message=record.getMessage(),
            logger_name=record.name,
            event=str(getattr(record, "event", "")),
            component=str(context.get("component", self._service)),
            environment=self._environment,
            correlation_id=str(context.get("correlation_id", "")),
            run_id=str(context.get("run_id", "")),
            process_id=record.process or 0,
            thread_name=record.threadName or "",
            module=record.module,
            function=record.funcName,
            line=record.lineno,
            exception=self.formatException(record.exc_info) if record.exc_info else "",
            metadata={
                key: _redact_value(key, value)
                for key, value in {**context, **metadata}.items()
                if key not in ("component", "correlation_id", "run_id")
            },
        )


class TextFormatter(JsonFormatter):
    """Same record, rendered for a human reading a console."""

    def format(self, record: logging.LogRecord) -> str:
        return self._build(record).to_text()


class StructuredLogger:
    """The logging interface the platform code uses (§13-14).

    Wraps a stdlib logger so callers never touch ``logging`` directly.
    That indirection is what makes the format, the sinks and the
    redaction rule changeable in one place.
    """

    def __init__(self, name: str, component: str = "") -> None:
        self._logger = logging.getLogger(name)
        self._component = component or name

    @property
    def name(self) -> str:
        return self._logger.name

    def bind(self, **values: Any) -> "BoundLogger":
        """A logger that adds ``values`` to every record it emits (§15)."""
        return BoundLogger(self, values)

    def _emit(self, level: int, message: str, event: str, fields: Dict[str, Any]) -> None:
        safe = {key: _redact_value(key, value) for key, value in fields.items()}
        with log_context(component=self._component):
            self._logger.log(
                level,
                message,
                extra={"event": event, "metadata": safe},
                exc_info=fields.get("exc_info", False) is True,
            )

    def debug(self, message: str, event: str = "", **fields: Any) -> None:
        self._emit(logging.DEBUG, message, event, fields)

    def info(self, message: str, event: str = "", **fields: Any) -> None:
        self._emit(logging.INFO, message, event, fields)

    def warning(self, message: str, event: str = "", **fields: Any) -> None:
        self._emit(logging.WARNING, message, event, fields)

    def error(self, message: str, event: str = "", **fields: Any) -> None:
        self._emit(logging.ERROR, message, event, fields)

    def critical(self, message: str, event: str = "", **fields: Any) -> None:
        self._emit(logging.CRITICAL, message, event, fields)

    def exception(self, message: str, event: str = "", **fields: Any) -> None:
        """Log an error with the active traceback attached."""
        safe = {key: _redact_value(key, value) for key, value in fields.items()}
        with log_context(component=self._component):
            self._logger.error(message, extra={"event": event, "metadata": safe}, exc_info=True)


class BoundLogger:
    """A logger carrying fixed fields (§15)."""

    def __init__(self, parent: StructuredLogger, values: Mapping[str, Any]) -> None:
        self._parent = parent
        self._values = dict(values)

    def bind(self, **values: Any) -> "BoundLogger":
        return BoundLogger(self._parent, {**self._values, **values})

    def _merge(self, fields: Dict[str, Any]) -> Dict[str, Any]:
        return {**self._values, **fields}

    def debug(self, message: str, event: str = "", **fields: Any) -> None:
        self._parent.debug(message, event, **self._merge(fields))

    def info(self, message: str, event: str = "", **fields: Any) -> None:
        self._parent.info(message, event, **self._merge(fields))

    def warning(self, message: str, event: str = "", **fields: Any) -> None:
        self._parent.warning(message, event, **self._merge(fields))

    def error(self, message: str, event: str = "", **fields: Any) -> None:
        self._parent.error(message, event, **self._merge(fields))

    def critical(self, message: str, event: str = "", **fields: Any) -> None:
        self._parent.critical(message, event, **self._merge(fields))

    def exception(self, message: str, event: str = "", **fields: Any) -> None:
        self._parent.exception(message, event, **self._merge(fields))


def configure_logging(
    level: str = "INFO",
    environment: str = "development",
    json_output: bool = False,
    log_file: Optional[str | Path] = None,
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    logger_levels: Optional[Mapping[str, str]] = None,
) -> logging.Logger:
    """Install the platform's logging configuration (§27-31).

    Console output is human-readable by default and JSON on request;
    a file sink, when configured, is always JSON and always rotated.
    An unrotated log file eventually fills the disk and takes the
    trading platform down with it.
    """
    normalised = level.strip().upper()
    if normalised not in LEVELS:
        raise ValueError(f"Unknown log level '{level}'. Use one of: {', '.join(LEVELS)}")

    root = logging.getLogger("ShadBotTrader")
    root.setLevel(getattr(logging, normalised))
    root.handlers.clear()
    root.propagate = False

    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(JsonFormatter(environment) if json_output else TextFormatter(environment))
    root.addHandler(console)

    if log_file:
        from logging.handlers import RotatingFileHandler

        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(
            path, maxBytes=max_bytes, backupCount=backup_count, encoding="utf-8"
        )
        handler.setFormatter(JsonFormatter(environment))
        root.addHandler(handler)

    for name, specific in (logger_levels or {}).items():
        logging.getLogger(name).setLevel(getattr(logging, specific.strip().upper()))

    return root


def get_logger(name: str, component: str = "") -> StructuredLogger:
    """The entry point every module uses to obtain a logger."""
    full = name if name.startswith("ShadBotTrader") else f"ShadBotTrader.{name}"
    return StructuredLogger(full, component)


def configure_from(config: Any) -> logging.Logger:
    """Configure logging from a :class:`LayeredConfiguration`."""
    return configure_logging(
        level=config.get_str("logging.level", "INFO"),
        environment=config.get_str("environment", "development"),
        json_output=config.get_bool("logging.json", False),
        log_file=config.get("logging.file"),
        max_bytes=config.get_int("logging.max_bytes", 10 * 1024 * 1024),
        backup_count=config.get_int("logging.backup_count", 5),
    )


def describe_runtime() -> Dict[str, Any]:
    """Facts worth attaching to a startup log line."""
    return {
        "pid": os.getpid(),
        "thread": threading.current_thread().name,
        "python": ".".join(str(part) for part in sys.version_info[:3]),
    }
