"""Tests for the dependency container."""

import pytest

from ShadBotTrader.core.dependency.container import DependencyContainer
from ShadBotTrader.core.errors import DependencyError


class ServiceA:
    def __init__(self, b: "ServiceB") -> None:
        self.b = b


class ServiceB:
    def __init__(self, a: "ServiceA") -> None:
        self.a = a


def test_register_and_resolve_instance():
    container = DependencyContainer()
    container.register_instance(str, "hello")
    assert container.resolve(str) == "hello"


def test_factory_creates_new_instances():
    container = DependencyContainer()
    container.register_factory(list, lambda _: [])
    assert container.resolve(list) is not container.resolve(list)


def test_singleton_caches_instance():
    container = DependencyContainer()
    container.register_singleton(dict, lambda _: {})
    assert container.resolve(dict) is container.resolve(dict)


def test_missing_dependency_raises():
    container = DependencyContainer()
    with pytest.raises(DependencyError):
        container.resolve(int)


def test_wrong_instance_type_rejected():
    container = DependencyContainer()
    with pytest.raises(DependencyError):
        container.register_instance(str, 42)


def test_circular_dependency_detected():
    container = DependencyContainer()
    container.register_factory(ServiceA, lambda c: ServiceA(c.resolve(ServiceB)))
    container.register_factory(ServiceB, lambda c: ServiceB(c.resolve(ServiceA)))
    with pytest.raises(DependencyError, match="Circular"):
        container.resolve(ServiceA)
