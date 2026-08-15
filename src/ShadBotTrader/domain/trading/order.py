"""Order entity and its supporting enums."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from ShadBotTrader.domain.common.entity import Entity
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.identifier import Identifier
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol


class OrderSide(str, Enum):
    """The direction of an order."""

    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    """The execution type of an order."""

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderStatus(str, Enum):
    """The lifecycle status of an order."""

    CREATED = "created"
    SUBMITTED = "submitted"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"


class Order(Entity[Identifier]):
    """A single trading order intent."""

    def __init__(
        self,
        symbol: Symbol,
        side: OrderSide,
        order_type: OrderType,
        quantity: Decimal,
        limit_price: Price | None = None,
        stop_price: Price | None = None,
        identifier: Identifier | None = None,
    ) -> None:
        if quantity <= 0:
            raise ValidationError("Order quantity must be positive")
        self._identifier = identifier or Identifier()
        self._symbol = symbol
        self._side = side
        self._order_type = order_type
        self._quantity = quantity
        self._limit_price = limit_price
        self._stop_price = stop_price
        self._status = OrderStatus.CREATED

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
    def order_type(self) -> OrderType:
        return self._order_type

    @property
    def quantity(self) -> Decimal:
        return self._quantity

    @property
    def limit_price(self) -> Price | None:
        return self._limit_price

    @property
    def stop_price(self) -> Price | None:
        return self._stop_price

    @property
    def status(self) -> OrderStatus:
        return self._status

    def submit(self) -> None:
        """Move the order from CREATED to SUBMITTED."""
        if self._status is not OrderStatus.CREATED:
            raise ValidationError(f"Cannot submit an order in state {self._status.value}")
        self._status = OrderStatus.SUBMITTED

    def fill(self) -> None:
        """Move the order into the FILLED state."""
        if self._status not in (OrderStatus.SUBMITTED, OrderStatus.PARTIALLY_FILLED):
            raise ValidationError(f"Cannot fill an order in state {self._status.value}")
        self._status = OrderStatus.FILLED

    def cancel(self) -> None:
        """Move the order into the CANCELLED state."""
        if self._status in (OrderStatus.FILLED, OrderStatus.CANCELLED, OrderStatus.REJECTED):
            raise ValidationError(f"Cannot cancel an order in state {self._status.value}")
        self._status = OrderStatus.CANCELLED
