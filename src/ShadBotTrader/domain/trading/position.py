"""Open position entity."""

from __future__ import annotations

from decimal import Decimal

from ShadBotTrader.domain.common.entity import Entity
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.identifier import Identifier
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.trading.order import OrderSide


class Position(Entity[Identifier]):
    """An open market position on a single symbol."""

    def __init__(
        self,
        symbol: Symbol,
        side: OrderSide,
        quantity: Decimal,
        average_entry_price: Price,
        identifier: Identifier | None = None,
    ) -> None:
        if quantity <= 0:
            raise ValidationError("Position quantity must be positive")
        self._identifier = identifier or Identifier()
        self._symbol = symbol
        self._side = side
        self._quantity = quantity
        self._average_entry_price = average_entry_price

    @property
    def id(self) -> Identifier:
        return self._identifier

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def side(self) -> OrderSide:
        return self._side

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def average_entry_price(self) -> Price:
        return self._average_entry_price

    @property
    def notional(self) -> Decimal:
        """The notional value of the position."""
        return self._quantity * self._average_entry_price.amount
