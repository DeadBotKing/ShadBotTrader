"""Market timeframe value object."""

from __future__ import annotations

from enum import Enum

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class TimeframeUnit(str, Enum):
    """The time unit of a timeframe."""

    MINUTE = "minute"
    HOUR = "hour"
    DAY = "day"


class Timeframe(ValueObject):
    """A candle period, e.g. ``5M``, ``15M``, ``1H``, ``4H``, ``1D``."""

    def __init__(self, value: str) -> None:
        label = value.strip().upper()
        unit, amount = self._parse(label)
        self._label = label
        self._unit = unit
        self._amount = amount

    @staticmethod
    def _parse(label: str) -> tuple[TimeframeUnit, int]:
        if len(label) < 2:
            raise ValidationError(f"Invalid timeframe: {label!r}")
        suffix = label[-1]
        prefix = label[:-1]
        if not prefix.isdigit():
            raise ValidationError(f"Invalid timeframe amount: {label!r}")
        amount = int(prefix)
        if amount <= 0:
            raise ValidationError(f"Timeframe amount must be positive: {label!r}")
        if suffix == "M":
            return TimeframeUnit.MINUTE, amount
        if suffix == "H":
            return TimeframeUnit.HOUR, amount
        if suffix == "D":
            return TimeframeUnit.DAY, amount
        raise ValidationError(f"Unknown timeframe suffix: {suffix!r}")

    @property
    def label(self) -> str:
        """The normalized label, e.g. ``5M``."""
        return self._label

    @property
    def unit(self) -> TimeframeUnit:
        """The time unit of this timeframe."""
        return self._unit

    @property
    def amount(self) -> int:
        """The numeric amount of this timeframe."""
        return self._amount

    def _value(self) -> tuple[str]:
        return (self._label,)

    def __str__(self) -> str:
        return self._label
