"""Structured, contextual logging — Phase 22."""

from ShadBotTrader.infrastructure.logging.structured import (
    BoundLogger,
    JsonFormatter,
    LogRecord,
    StructuredLogger,
    TextFormatter,
    configure_from,
    configure_logging,
    correlation_scope,
    current_context,
    get_logger,
    log_context,
    new_correlation_id,
)

__all__ = [
    "BoundLogger",
    "JsonFormatter",
    "LogRecord",
    "StructuredLogger",
    "TextFormatter",
    "configure_from",
    "configure_logging",
    "correlation_scope",
    "current_context",
    "get_logger",
    "log_context",
    "new_correlation_id",
]
