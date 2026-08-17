"""Configuration loading, layering and typed access — Phase 21."""

from ShadBotTrader.infrastructure.configuration.configuration import (
    Configuration,
    ConfigurationError,
)
from ShadBotTrader.infrastructure.configuration.layered import (
    ENVIRONMENTS,
    REDACTED,
    ConfigurationLoader,
    LayeredConfiguration,
    SourceRecord,
    ValidationRule,
    deep_merge,
    default_rules,
    flatten,
    is_secret_key,
    redact,
)

__all__ = [
    "ENVIRONMENTS",
    "REDACTED",
    "Configuration",
    "ConfigurationError",
    "ConfigurationLoader",
    "LayeredConfiguration",
    "SourceRecord",
    "ValidationRule",
    "deep_merge",
    "default_rules",
    "flatten",
    "is_secret_key",
    "redact",
]
