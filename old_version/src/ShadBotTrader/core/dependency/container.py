"""A small, explicit dependency container used by the composition root."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Type, TypeVar, cast

from ShadBotTrader.core.errors import DependencyError

T = TypeVar("T")
Factory = Callable[["DependencyContainer"], Any]


class DependencyContainer:
    """Resolves dependencies that the composition root registers.

    Supported registrations:

    * ``register_instance``  - a pre-built singleton object.
    * ``register_singleton`` - a factory evaluated once, then cached.
    * ``register_factory``   - a factory evaluated on every resolution.

    Factories receive the container itself so they can resolve their own
    dependencies. Circular dependencies are detected and rejected.
    """

    def __init__(self) -> None:
        self._instances: Dict[Type[Any], Any] = {}
        self._singletons: Dict[Type[Any], Factory] = {}
        self._factories: Dict[Type[Any], Factory] = {}
        self._resolving: List[Type[Any]] = []

    def register_instance(self, dependency_type: Type[T], instance: T) -> None:
        """Register an already-built object as a singleton."""
        if not isinstance(instance, dependency_type):
            raise DependencyError(
                f"Instance {instance!r} is not of type {dependency_type.__name__}"
            )
        self._check_conflict(dependency_type)
        self._instances[dependency_type] = instance

    def register_singleton(self, dependency_type: Type[T], factory: Factory) -> None:
        """Register a factory whose result is built once and then cached."""
        self._check_conflict(dependency_type)
        self._singletons[dependency_type] = factory

    def register_factory(self, dependency_type: Type[T], factory: Factory) -> None:
        """Register a factory whose result is rebuilt on every resolution."""
        self._check_conflict(dependency_type)
        self._factories[dependency_type] = factory

    def resolve(self, dependency_type: Type[T]) -> T:
        """Resolve a registered dependency, building it when necessary."""
        if dependency_type in self._instances:
            return cast(T, self._instances[dependency_type])
        if dependency_type in self._singletons:
            instance = self._build(dependency_type, self._singletons[dependency_type])
            self._instances[dependency_type] = instance
            return cast(T, instance)
        if dependency_type in self._factories:
            return cast(T, self._build(dependency_type, self._factories[dependency_type]))
        raise DependencyError(f"No registration found for {dependency_type.__name__}")

    def has(self, dependency_type: Type[Any]) -> bool:
        """Return True when a registration exists for ``dependency_type``."""
        return (
            dependency_type in self._instances
            or dependency_type in self._singletons
            or dependency_type in self._factories
        )

    def _build(self, dependency_type: Type[Any], factory: Factory) -> Any:
        if dependency_type in self._resolving:
            cycle = " -> ".join(type_.__name__ for type_ in (*self._resolving, dependency_type))
            raise DependencyError(f"Circular dependency detected: {cycle}")
        self._resolving.append(dependency_type)
        try:
            return factory(self)
        finally:
            self._resolving.pop()

    def _check_conflict(self, dependency_type: Type[Any]) -> None:
        if self.has(dependency_type):
            raise DependencyError(f"{dependency_type.__name__} is already registered")
