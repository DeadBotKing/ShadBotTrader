"""Trading symbol value object."""

from __future__ import annotations

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class Symbol(ValueObject):
    """A tradable instrument identifier, e.g. ``XAUUSD_i``."""

    def __init__(self, value: str) -> None:
        normalized = value.strip()
        if not normalized:
            raise ValidationError("Symbol must not be empty")
        if any(character.isspace() for character in normalized):
            raise ValidationError(f"Symbol must not contain whitespace: {value!r}")
        self._value_field = normalized

    @property
    def value(self) -> str:
        """The normalized symbol label."""
        return self._value_field

    def _value(self) -> tuple[str]:
        return (self._value_field,)

    def __str__(self) -> str:
        return self._value_field
