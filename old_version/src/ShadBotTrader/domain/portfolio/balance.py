"""Account balance value object."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class Balance(ValueObject):
    """An amount of money in a single currency."""

    def __init__(self, amount: Decimal | int | float | str, currency: str) -> None:
        value = self._coerce(amount)
        if value < 0:
            raise ValidationError(f"Balance must not be negative, got {value}")
        normalized_currency = currency.strip().upper()
        if not normalized_currency:
            raise ValidationError("currency must not be empty")
        self._amount = value
        self._currency = normalized_currency

    @staticmethod
    def _coerce(value: Decimal | int | float | str) -> Decimal:
        try:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, float):
                return Decimal(str(value))
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"Invalid balance value: {value!r}") from exc

    @property
    def amount(self) -> Decimal:
        return self._amount

    @property
    def currency(self) -> str:
        return self._currency

    def _value(self) -> tuple[Any, ...]:
        return (self._amount, self._currency)

    def __str__(self) -> str:
        return f"{self._amount} {self._currency}"
