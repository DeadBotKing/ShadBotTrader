"""Risk state value object."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class RiskState(ValueObject):
    """A snapshot of the current risk exposure.

    ``max_drawdown_percent`` and ``max_daily_loss_percent`` are expressed
    in percent (0..100); ``exposure_ratio`` is expressed as a ratio
    (0..1).
    """

    def __init__(
        self,
        max_drawdown_percent: Decimal,
        max_daily_loss_percent: Decimal,
        exposure_ratio: Decimal,
    ) -> None:
        self._max_drawdown_percent = self._coerce(max_drawdown_percent, "max_drawdown_percent")
        self._max_daily_loss_percent = self._coerce(
            max_daily_loss_percent, "max_daily_loss_percent"
        )
        self._exposure_ratio = self._coerce(exposure_ratio, "exposure_ratio")

        if not 0 <= self._max_drawdown_percent <= 100:
            raise ValidationError("max_drawdown_percent must be in [0, 100]")
        if not 0 <= self._max_daily_loss_percent <= 100:
            raise ValidationError("max_daily_loss_percent must be in [0, 100]")
        if not 0 <= self._exposure_ratio <= 1:
            raise ValidationError("exposure_ratio must be in [0, 1]")

    @staticmethod
    def _coerce(value: Decimal | int | float | str, name: str) -> Decimal:
        try:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, float):
                return Decimal(str(value))
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"Invalid {name} value: {value!r}") from exc

    @property
    def max_drawdown_percent(self) -> Decimal:
        return self._max_drawdown_percent

    @property
    def max_daily_loss_percent(self) -> Decimal:
        return self._max_daily_loss_percent

    @property
    def exposure_ratio(self) -> Decimal:
        return self._exposure_ratio

    def _value(self) -> tuple[Any, ...]:
        return (
            self._max_drawdown_percent,
            self._max_daily_loss_percent,
            self._exposure_ratio,
        )
