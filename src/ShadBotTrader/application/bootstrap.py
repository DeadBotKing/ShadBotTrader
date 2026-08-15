"""Composition root: builds and wires the application object graph."""

from __future__ import annotations

import logging
from pathlib import Path

from ShadBotTrader.application.app import Application
from ShadBotTrader.application.service_registry import ServiceRegistry
from ShadBotTrader.core.dependency.container import DependencyContainer
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.core.lifecycle.lifecycle_manager import LifecycleManager
from ShadBotTrader.infrastructure.configuration.configuration import (
    Configuration,
    YamlConfigurationLoader,
)
from ShadBotTrader.infrastructure.logging.logging_setup import (
    configure_logging,
    get_logger,
)

DEFAULT_CONFIG_PATH = Path("configs/app.yaml")


class Bootstrap:
    """Builds the fully wired application object graph."""

    def __init__(self, configuration: Configuration | None = None) -> None:
        self._configuration = configuration

    def build(self) -> Application:
        """Assemble and wire the application."""
        configuration = self._configuration or self._load_configuration()
        self._configure_logging(configuration)
        logger = get_logger("ShadBotTrader.application")

        container = DependencyContainer()
        event_bus = EventBus()
        lifecycle = LifecycleManager()
        registry = ServiceRegistry()

        container.register_instance(DependencyContainer, container)
        container.register_instance(Configuration, configuration)
        container.register_instance(EventBus, event_bus)
        container.register_instance(LifecycleManager, lifecycle)
        container.register_instance(ServiceRegistry, registry)

        return Application(
            container=container,
            event_bus=event_bus,
            lifecycle=lifecycle,
            registry=registry,
            configuration=configuration,
            logger=logger,
        )

    def _load_configuration(self) -> Configuration:
        loader = YamlConfigurationLoader()
        if DEFAULT_CONFIG_PATH.exists():
            return loader.load(DEFAULT_CONFIG_PATH)
        return Configuration(
            {
                "app": {"name": "ShadBotTrader", "version": "0.1.0"},
                "logging": {"level": "INFO"},
            }
        )

    @staticmethod
    def _configure_logging(configuration: Configuration) -> None:
        level_name = configuration.get_str("logging.level", default="INFO")
        level = getattr(logging, level_name.upper(), logging.INFO)
        configure_logging(level=level)
