"""Trading account aggregate root."""

from __future__ import annotations

from ShadBotTrader.domain.common.entity import Entity
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.identifier import Identifier
from ShadBotTrader.domain.portfolio.balance import Balance


class Account(Entity[Identifier]):
    """A trading account identified by id and holding a balance."""

    def __init__(self, balance: Balance, identifier: Identifier | None = None) -> None:
        self._identifier = identifier or Identifier()
        self._balance = balance

    @property
    def id(self) -> Identifier:
        return self._identifier

    @property
    def balance(self) -> Balance:
        """The current balance of the account."""
        return self._balance

    def deposit(self, amount: Balance) -> None:
        """Increase the balance by ``amount`` in the same currency."""
        self._require_same_currency(amount)
        self._balance = Balance(self._balance.amount + amount.amount, self._balance.currency)

    def withdraw(self, amount: Balance) -> None:
        """Decrease the balance by ``amount`` in the same currency."""
        self._require_same_currency(amount)
        if amount.amount > self._balance.amount:
            raise ValidationError("Insufficient balance")
        self._balance = Balance(self._balance.amount - amount.amount, self._balance.currency)

    def _require_same_currency(self, amount: Balance) -> None:
        if amount.currency != self._balance.currency:
            raise ValidationError(
                f"Currency mismatch: {amount.currency} vs {self._balance.currency}"
            )
