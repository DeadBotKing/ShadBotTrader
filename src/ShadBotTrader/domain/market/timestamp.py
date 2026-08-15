"""Timezone-aware timestamp value object."""

from __future__ import annotations

from datetime import datetime

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class Timestamp(ValueObject):
    """A point in time; the domain only accepts timezone-aware values."""

    def __init__(self, value: datetime) -> None:
        if value.tzinfo is None or value.tzinfo.utcoffset(value) is None:
            raise ValidationError("Timestamp must be timezone-aware")
        self._value_field = value

    @property
    def value(self) -> datetime:
        """The underlying datetime."""
        return self._value_field

    def _value(self) -> tuple[datetime]:
        return (self._value_field,)

    def __str__(self) -> str:
        return self._value_field.isoformat()
