"""Tests for the application bootstrap and runtime."""

from ShadBotTrader.application.application_state import ApplicationState
from ShadBotTrader.application.bootstrap import Bootstrap
from ShadBotTrader.application.runtime import Runtime
from ShadBotTrader.core.dependency.container import DependencyContainer
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.core.lifecycle.lifecycle_manager import LifecycleManager
from ShadBotTrader.infrastructure.configuration.configuration import Configuration


def test_application_boots_and_shuts_down_cleanly():
    application = Bootstrap().build()
    assert application.state is ApplicationState.CREATED

    exit_code = Runtime(application).run()

    assert exit_code == 0
    assert application.state is ApplicationState.STOPPED


def test_dependencies_are_wired_into_container():
    application = Bootstrap().build()
    assert application.container.resolve(EventBus) is application.event_bus
    assert application.container.resolve(LifecycleManager) is application.lifecycle
    assert application.container.resolve(DependencyContainer) is application.container


def test_configuration_defaults_apply_when_no_file_given():
    configuration = Configuration({"logging": {"level": "WARNING"}})
    application = Bootstrap(configuration=configuration).build()
    assert application.configuration.get_str("logging.level") == "WARNING"
