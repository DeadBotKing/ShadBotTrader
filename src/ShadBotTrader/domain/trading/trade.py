"""Trade (execution fill) entity."""

from __future__ import annotations

from decimal import Decimal

from ShadBotTrader.domain.common.entity import Entity
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.identifier import Identifier
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.trading.order import OrderSide


class Trade(Entity[Identifier]):
    """A single execution fill."""

    def __init__(
        self,
        order_id: Identifier,
        symbol: Symbol,
        side: OrderSide,
        price: Price,
        quantity: Decimal,
        executed_at: Timestamp,
        identifier: Identifier | None = None,
    ) -> None:
        if quantity <= 0:
            raise ValidationError("Trade quantity must be positive")
        self._identifier = identifier or Identifier()
        self._order_id = order_id
        self._symbol = symbol
        self._side = side
        self._price = price
        self._quantity = quantity
        self._executed_at = executed_at

    @property
    def id(self) -> Identifier:
        return self._identifier

    @property
    def order_id(self) -> Identifier:
        """The order this trade filled."""
        return self._order_id

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def side(self) -> OrderSide:
        return self._side

    @property
    def price(self) -> Price:
        return self._price

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def executed_at(self) -> Timestamp:
        return self._executed_at

    @property
    def notional(self) -> Decimal:
        """The notional value of the fill."""
        return self._price.amount * self._quantity
