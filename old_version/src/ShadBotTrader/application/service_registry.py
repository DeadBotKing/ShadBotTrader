"""Named lookup table for runtime services."""

from __future__ import annotations

from typing import Any, Dict

from ShadBotTrader.core.errors import ServiceError


class ServiceRegistry:
    """A named registry of runtime services.

    Services are registered by a unique name and looked up by the same
    name. The registry is intentionally dumb: it performs no lifecycle
    management of its own.
    """

    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}

    def register(self, name: str, service: Any) -> None:
        """Register ``service`` under ``name``."""
        if not name.strip():
            raise ServiceError("Service name must not be empty")
        if name in self._services:
            raise ServiceError(f"Service '{name}' is already registered")
        self._services[name] = service

    def get(self, name: str) -> Any:
        """Return the service registered under ``name``."""
        if name not in self._services:
            raise ServiceError(f"Unknown service '{name}'")
        return self._services[name]

    def contains(self, name: str) -> bool:
        """Return True when a service is registered under ``name``."""
        return name in self._services

    def names(self) -> list[str]:
        """Return the registered service names."""
        return list(self._services.keys())
