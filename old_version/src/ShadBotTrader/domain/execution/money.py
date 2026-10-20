"""Money value object (Phase 15, sections 17-18).

Every financial amount in the platform carries its currency. Unlike
``Balance`` (which is an account holding and may not be negative), Money
is a signed quantity: PnL, fees and adjustments can all be negative.

Arithmetic uses ``Decimal`` exclusively — float is forbidden for
financial accounting (Phase 15, section 15).
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class Money(ValueObject):
    """A signed monetary amount in a single currency."""

    def __init__(self, amount: Decimal | int | float | str, currency: str) -> None:
        self._money_amount = self._coerce(amount)
        normalized = currency.strip().upper()
        if not normalized:
            raise ValidationError("Money currency must not be empty")
        self._currency = normalized

    @staticmethod
    def _coerce(value: Decimal | int | float | str) -> Decimal:
        try:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, float):
                return Decimal(str(value))
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"Invalid money value: {value!r}") from exc

    @classmethod
    def zero(cls, currency: str) -> "Money":
        """A zero amount in ``currency``."""
        return cls(Decimal("0"), currency)

    @property
    def amount(self) -> Decimal:
        return self._money_amount

    @property
    def currency(self) -> str:
        return self._currency

    @property
    def is_zero(self) -> bool:
        return self._money_amount == 0

    @property
    def is_positive(self) -> bool:
        return self._money_amount > 0

    @property
    def is_negative(self) -> bool:
        return self._money_amount < 0

    def _require_same_currency(self, other: "Money") -> None:
        if self._currency != other.currency:
            raise ValidationError(f"Currency mismatch: {self._currency} vs {other.currency}")

    def add(self, other: "Money") -> "Money":
        """Return the sum; both operands must share a currency."""
        self._require_same_currency(other)
        return Money(self._money_amount + other.amount, self._currency)

    def subtract(self, other: "Money") -> "Money":
        """Return the difference; both operands must share a currency."""
        self._require_same_currency(other)
        return Money(self._money_amount - other.amount, self._currency)

    def scale(self, factor: Decimal | int | str) -> "Money":
        """Return the amount multiplied by ``factor``."""
        return Money(self._money_amount * self._coerce(factor), self._currency)

    def negate(self) -> "Money":
        """Return the amount with the opposite sign."""
        return Money(-self._money_amount, self._currency)

    def __add__(self, other: "Money") -> "Money":
        return self.add(other)

    def __sub__(self, other: "Money") -> "Money":
        return self.subtract(other)

    def __neg__(self) -> "Money":
        return self.negate()

    def _value(self) -> tuple[Any, ...]:
        return (self._money_amount, self._currency)

    def __str__(self) -> str:
        return f"{self._money_amount} {self._currency}"
