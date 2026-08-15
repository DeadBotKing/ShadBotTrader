"""Base class for entities (objects with identity)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

T = TypeVar("T")


class Entity(ABC, Generic[T]):
    """A domain object distinguished by identity rather than attributes.

    Two entities are equal only when they share the same concrete type
    and the same identity.
    """

    @property
    @abstractmethod
    def id(self) -> T:
        """The unique identity of the entity."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Entity):
            return False
        return type(self) is type(other) and self.id == other.id

    def __hash__(self) -> int:
        return hash((type(self), self.id))
