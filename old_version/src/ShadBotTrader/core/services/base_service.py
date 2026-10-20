"""Base service contract shared by every runtime service."""

from __future__ import annotations

from ShadBotTrader.core.errors import LifecycleError, ServiceError
from ShadBotTrader.core.lifecycle.lifecycle_manager import LifecycleAware, LifecycleState


class BaseService(LifecycleAware):
    """A named component with a guarded ``start``/``stop`` lifecycle.

    Subclasses override :meth:`on_start` and :meth:`on_stop` to plug in
    their own behaviour; the base class owns the state machine and
    rejects illegal transitions.
    """

    def __init__(self, name: str) -> None:
        if not name.strip():
            raise ServiceError("Service name must not be empty")
        self._name = name
        self._state = LifecycleState.CREATED

    @property
    def name(self) -> str:
        """The service name."""
        return self._name

    @property
    def state(self) -> LifecycleState:
        """The current lifecycle state of the service."""
        return self._state

    def start(self) -> None:
        """Move the service into the RUNNING state."""
        if self._state in (LifecycleState.STARTING, LifecycleState.RUNNING):
            raise LifecycleError(f"Service '{self._name}' has already been started")
        self._state = LifecycleState.STARTING
        self.on_start()
        self._state = LifecycleState.RUNNING

    def stop(self) -> None:
        """Move the service into the STOPPED state."""
        if self._state in (
            LifecycleState.CREATED,
            LifecycleState.STOPPING,
            LifecycleState.STOPPED,
        ):
            raise LifecycleError(f"Service '{self._name}' is not running")
        self._state = LifecycleState.STOPPING
        self.on_stop()
        self._state = LifecycleState.STOPPED

    def on_start(self) -> None:
        """Hook invoked between STARTING and RUNNING. Default is a no-op."""
        return None

    def on_stop(self) -> None:
        """Hook invoked between STOPPING and STOPPED. Default is a no-op."""
        return None
