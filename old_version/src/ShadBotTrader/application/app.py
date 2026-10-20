"""The application object graph assembled by the composition root."""

from __future__ import annotations

import logging

from ShadBotTrader.application.application_state import ApplicationState
from ShadBotTrader.application.service_registry import ServiceRegistry
from ShadBotTrader.core.dependency.container import DependencyContainer
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.core.lifecycle.lifecycle_manager import LifecycleManager
from ShadBotTrader.infrastructure.configuration.configuration import Configuration


class Application:
    """The wired object graph of a running ShadBotTrader application."""

    def __init__(
        self,
        container: DependencyContainer,
        event_bus: EventBus,
        lifecycle: LifecycleManager,
        registry: ServiceRegistry,
        configuration: Configuration,
        logger: logging.Logger,
    ) -> None:
        self._container = container
        self._event_bus = event_bus
        self._lifecycle = lifecycle
        self._registry = registry
        self._configuration = configuration
        self._logger = logger
        self._state = ApplicationState.CREATED

    @property
    def container(self) -> DependencyContainer:
        return self._container

    @property
    def event_bus(self) -> EventBus:
        return self._event_bus

    @property
    def lifecycle(self) -> LifecycleManager:
        return self._lifecycle

    @property
    def registry(self) -> ServiceRegistry:
        return self._registry

    @property
    def configuration(self) -> Configuration:
        return self._configuration

    @property
    def logger(self) -> logging.Logger:
        return self._logger

    @property
    def state(self) -> ApplicationState:
        """The current application state."""
        return self._state

    def transition(self, state: ApplicationState) -> None:
        """Move the application to ``state`` and log the transition."""
        self._state = state
        self._logger.info("Application state -> %s", state.value)
