"""Candle entity with strict OHLC invariants."""

from __future__ import annotations

from decimal import Decimal

from ShadBotTrader.domain.common.entity import Entity
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.identifier import Identifier
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp


class Candle(Entity[Identifier]):
    """A single OHLCV candle for one symbol and timeframe.

    Invariants enforced at construction:

    * every price is positive
    * ``high >= low``
    * ``high >= max(open, close)``
    * ``low <= min(open, close)``
    * volume is non-negative
    """

    def __init__(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        open_time: Timestamp,
        open_price: Price,
        high: Price,
        low: Price,
        close: Price,
        volume: Decimal,
        identifier: Identifier | None = None,
    ) -> None:
        if volume < 0:
            raise ValidationError("Candle volume must not be negative")
        if high.amount < low.amount:
            raise ValidationError("Candle high must be >= low")
        if high.amount < max(open_price.amount, close.amount):
            raise ValidationError("Candle high must be >= open and close")
        if low.amount > min(open_price.amount, close.amount):
            raise ValidationError("Candle low must be <= open and close")

        self._identifier = identifier or Identifier()
        self._symbol = symbol
        self._timeframe = timeframe
        self._open_time = open_time
        self._open = open_price
        self._high = high
        self._low = low
        self._close = close
        self._volume = volume

    @property
    def id(self) -> Identifier:
        return self._identifier

    @property
    def symbol(self) -> Symbol:
        """The instrument of this candle."""
        return self._symbol

    @property
    def timeframe(self) -> Timeframe:
        """The period of this candle."""
        return self._timeframe

    @property
    def open_time(self) -> Timestamp:
        """The UTC open time of this candle."""
        return self._open_time

    @property
    def open(self) -> Price:
        return self._open

    @property
    def high(self) -> Price:
        return self._high

    @property
    def low(self) -> Price:
        return self._low

    @property
    def close(self) -> Price:
        return self._close

    @property
    def volume(self) -> Decimal:
        """The traded volume of this candle."""
        return self._volume

    @property
    def is_bullish(self) -> bool:
        """True when the candle closed at or above its open."""
        return self._close.amount >= self._open.amount

    @property
    def range(self) -> Decimal:
        """The high-low range of the candle."""
        return self._high.amount - self._low.amount
