"""Tests for the base service lifecycle."""

import pytest

from ShadBotTrader.core.errors import LifecycleError
from ShadBotTrader.core.lifecycle.lifecycle_manager import LifecycleState
from ShadBotTrader.core.services.base_service import BaseService


class GreeterService(BaseService):
    def __init__(self) -> None:
        super().__init__(name="greeter")
        self.started = False
        self.stopped = False

    def on_start(self) -> None:
        self.started = True

    def on_stop(self) -> None:
        self.stopped = True


def test_service_lifecycle_transitions():
    service = GreeterService()
    assert service.state is LifecycleState.CREATED
    service.start()
    assert service.state is LifecycleState.RUNNING
    assert service.started is True
    service.stop()
    assert service.state is LifecycleState.STOPPED
    assert service.stopped is True


def test_double_start_raises():
    service = GreeterService()
    service.start()
    with pytest.raises(LifecycleError):
        service.start()


def test_stop_without_start_raises():
    service = GreeterService()
    with pytest.raises(LifecycleError):
        service.stop()
