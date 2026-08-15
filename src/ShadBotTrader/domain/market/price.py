"""Price value object with exact decimal arithmetic."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class Price(ValueObject):
    """A positive money price with exact decimal semantics."""

    def __init__(self, value: Decimal | int | float | str) -> None:
        amount = self._coerce(value)
        if amount <= 0:
            raise ValidationError(f"Price must be positive, got {amount}")
        self._amount = amount

    @staticmethod
    def _coerce(value: Decimal | int | float | str) -> Decimal:
        try:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, float):
                return Decimal(str(value))
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"Invalid price value: {value!r}") from exc

    @property
    def amount(self) -> Decimal:
        """The exact decimal amount."""
        return self._amount

    def _value(self) -> tuple[Decimal]:
        return (self._amount,)

    def __str__(self) -> str:
        return str(self._amount)
