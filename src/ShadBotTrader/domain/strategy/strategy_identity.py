"""Strategy identity value objects (Phase 14, sections 7-8)."""

from __future__ import annotations

from typing import Any

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class StrategyId(ValueObject):
    """The stable identity of a strategy, e.g. ``ai_directional``."""

    def __init__(self, value: str) -> None:
        normalized = value.strip().lower()
        if not normalized:
            raise ValidationError("StrategyId must not be empty")
        if any(char.isspace() for char in normalized):
            raise ValidationError("StrategyId must not contain whitespace")
        self._value_field = normalized

    @property
    def value(self) -> str:
        return self._value_field

    def _value(self) -> tuple[Any, ...]:
        return (self._value_field,)

    def __str__(self) -> str:
        return self._value_field


class StrategyVersion(ValueObject):
    """An immutable strategy version number (Phase 14, section 8)."""

    def __init__(self, number: int) -> None:
        if number < 1:
            raise ValidationError("StrategyVersion must be >= 1")
        self._number = number

    @property
    def number(self) -> int:
        return self._number

    def next(self) -> "StrategyVersion":
        """Return the following version (versions are immutable)."""
        return StrategyVersion(self._number + 1)

    def _value(self) -> tuple[Any, ...]:
        return (self._number,)

    def __str__(self) -> str:
        return f"v{self._number}"
