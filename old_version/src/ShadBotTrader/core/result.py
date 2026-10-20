"""A minimal, type-safe Result type used across the platform.

The Result type makes success and failure explicit in the type system so
callers cannot accidentally ignore an error path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Optional, TypeVar, cast

T = TypeVar("T")


@dataclass(frozen=True)
class Result(Generic[T]):
    """The outcome of an operation that may fail.

    Exactly one of ``value`` or ``error`` is set: ``value`` on success,
    ``error`` on failure.
    """

    value: Optional[T]
    error: Optional[Exception]

    def __post_init__(self) -> None:
        if self.value is not None and self.error is not None:
            raise ValueError("Result cannot hold both a value and an error")

    @property
    def is_ok(self) -> bool:
        """Return True when the result represents a success."""
        return self.error is None

    @property
    def is_failure(self) -> bool:
        """Return True when the result represents a failure."""
        return self.error is not None

    def unwrap(self) -> T:
        """Return the success value or raise the underlying error."""
        error = self.error
        if error is not None:
            raise error
        return cast(T, self.value)

    def unwrap_or(self, default: T) -> T:
        """Return the success value, or ``default`` on failure."""
        if self.error is not None:
            return default
        return cast(T, self.value)

    @classmethod
    def ok(cls, value: T) -> "Result[T]":
        """Build a success result carrying ``value``."""
        return cls(value=value, error=None)

    @classmethod
    def fail(cls, error: Exception) -> "Result[Any]":
        """Build a failure result carrying ``error``."""
        return cls(value=None, error=error)
