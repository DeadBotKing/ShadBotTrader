"""Base class for value objects."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Tuple


class ValueObject(ABC):
    """A domain object with no identity, compared by the value it holds.

    Subclasses implement :meth:`_value`, which returns the tuple of
    fields that participate in equality and hashing.
    """

    @abstractmethod
    def _value(self) -> Tuple[Any, ...]:
        """Return the fields that define the value of this object."""

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, type(self)):
            return False
        return self._value() == other._value()

    def __hash__(self) -> int:
        return hash((type(self), self._value()))

    def __repr__(self) -> str:
        values = ", ".join(repr(value) for value in self._value())
        return f"{type(self).__name__}({values})"
