"""Tests for the lifecycle manager."""

import pytest

from ShadBotTrader.core.errors import LifecycleError
from ShadBotTrader.core.lifecycle.lifecycle_manager import LifecycleAware, LifecycleManager


class FakeComponent(LifecycleAware):
    def __init__(self, name: str, log: list[str]) -> None:
        self.name = name
        self.log = log
        self.started = False
        self.stopped = False

    def start(self) -> None:
        self.started = True
        self.log.append(f"{self.name}:start")

    def stop(self) -> None:
        self.stopped = True
        self.log.append(f"{self.name}:stop")


def test_start_in_order_stop_in_reverse():
    manager = LifecycleManager()
    log: list[str] = []
    first = FakeComponent("first", log)
    second = FakeComponent("second", log)
    manager.register(first)
    manager.register(second)

    manager.start()
    manager.stop()

    assert log == ["first:start", "second:start", "second:stop", "first:stop"]
    assert manager.is_started is True
    assert manager.is_stopped is True


def test_stop_before_start_raises():
    manager = LifecycleManager()
    with pytest.raises(LifecycleError):
        manager.stop()


def test_duplicate_registration_raises():
    manager = LifecycleManager()
    component = FakeComponent("first", [])
    manager.register(component)
    with pytest.raises(LifecycleError):
        manager.register(component)


def test_registration_after_start_raises():
    manager = LifecycleManager()
    manager.start()
    with pytest.raises(LifecycleError):
        manager.register(FakeComponent("late", []))
