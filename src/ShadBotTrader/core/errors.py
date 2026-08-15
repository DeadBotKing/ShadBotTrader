"""Core error hierarchy for the ShadBotTrader platform.

Every error raised by the core framework derives from
``ShadBotTraderError`` so callers can catch platform errors with one
stable type. Domain errors are intentionally defined inside the domain
layer (``ShadBotTrader.domain.common.errors``) so the domain stays
independent from the core framework.
"""


class ShadBotTraderError(Exception):
    """Base class for every error raised by the ShadBotTrader core."""


class EventError(ShadBotTraderError):
    """Raised when an event cannot be published or dispatched."""


class LifecycleError(ShadBotTraderError):
    """Raised for illegal lifecycle state transitions."""


class DependencyError(ShadBotTraderError):
    """Raised when a dependency cannot be registered or resolved."""


class PluginError(ShadBotTraderError):
    """Raised for plugin loading, registration or lifecycle failures."""


class ServiceError(ShadBotTraderError):
    """Raised for service-level failures."""
