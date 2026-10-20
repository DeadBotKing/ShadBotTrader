"""Ordered lifecycle management for startable/stoppable components."""

from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum

from ShadBotTrader.core.errors import LifecycleError


class LifecycleState(str, Enum):
    """The coarse lifecycle states a component may pass through."""

    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"


class LifecycleAware(ABC):
    """Contract implemented by every component with a runtime lifecycle."""

    @abstractmethod
    def start(self) -> None:
        """Transition the component into its running state."""

    @abstractmethod
    def stop(self) -> None:
        """Transition the component into its stopped state."""


class LifecycleManager:
    """Starts and stops registered components in deterministic order.

    Components start in registration order and stop in reverse order so
    dependencies tear down after the components that depend on them.
    """

    def __init__(self) -> None:
        self._components: list[LifecycleAware] = []
        self._started = False
        self._stopped = False

    @property
    def components(self) -> list[LifecycleAware]:
        """A snapshot copy of the registered components."""
        return list(self._components)

    @property
    def is_started(self) -> bool:
        """True once :meth:`start` has been called."""
        return self._started

    @property
    def is_stopped(self) -> bool:
        """True once :meth:`stop` has been called."""
        return self._stopped

    def register(self, component: LifecycleAware) -> None:
        """Register a component before startup begins."""
        if self._started:
            raise LifecycleError("Cannot register components after startup")
        if component in self._components:
            raise LifecycleError("Component is already registered")
        self._components.append(component)

    def start(self) -> None:
        """Start every registered component in registration order."""
        if self._started:
            raise LifecycleError("Lifecycle has already been started")
        self._started = True
        for component in self._components:
            component.start()

    def stop(self) -> None:
        """Stop every registered component in reverse registration order."""
        if not self._started:
            raise LifecycleError("Lifecycle has not been started")
        if self._stopped:
            raise LifecycleError("Lifecycle has already been stopped")
        for component in reversed(self._components):
            component.stop()
        self._stopped = True
