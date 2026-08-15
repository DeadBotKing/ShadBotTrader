"""Dataset version value object."""

from __future__ import annotations

from typing import Any

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class DatasetVersion(ValueObject):
    """A monotonic version number for a dataset.

    Versions start at 1. Every new ingestion of the same dataset identity
    produces a new, strictly higher version; previous versions are never
    overwritten (raw immutability).
    """

    def __init__(self, number: int) -> None:
        if isinstance(number, bool) or not isinstance(number, int):
            raise ValidationError(f"DatasetVersion must be an integer, got {number!r}")
        if number < 1:
            raise ValidationError(f"DatasetVersion must be >= 1, got {number}")
        self._number = number

    @property
    def number(self) -> int:
        return self._number

    def next(self) -> "DatasetVersion":
        """Return the version that follows this one."""
        return DatasetVersion(self._number + 1)

    def _value(self) -> tuple[Any, ...]:
        return (self._number,)

    def __str__(self) -> str:
        return str(self._number)
