"""Execution-time state (Phase 15, sections 12, 21).

``ExecutionContext`` is what the Execution Platform is allowed to see
when it resolves a policy into a number and when a venue prices a fill:
the current market, the account equity and the position already held.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp


class MarketQuote:
    """The tradable prices of a symbol at a point in time."""

    def __init__(
        self,
        symbol: Symbol,
        bid: Price,
        ask: Price,
        timestamp: Timestamp,
    ) -> None:
        if ask.amount < bid.amount:
            raise ValidationError("Ask must not be below bid")
        self._symbol = symbol
        self._bid = bid
        self._ask = ask
        self._timestamp = timestamp

    @classmethod
    def from_mid(
        cls,
        symbol: Symbol,
        mid: Price,
        spread: Decimal,
        timestamp: Timestamp,
    ) -> "MarketQuote":
        """Build a symmetric quote around ``mid`` with ``spread``."""
        if spread < 0:
            raise ValidationError("Spread must not be negative")
        half = spread / Decimal("2")
        return cls(
            symbol=symbol,
            bid=Price(mid.amount - half),
            ask=Price(mid.amount + half),
            timestamp=timestamp,
        )

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def bid(self) -> Price:
        return self._bid

    @property
    def ask(self) -> Price:
        return self._ask

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def mid(self) -> Price:
        return Price((self._bid.amount + self._ask.amount) / Decimal("2"))

    @property
    def spread(self) -> Decimal:
        return self._ask.amount - self._bid.amount


class ExecutionContext:
    """Everything the Execution Platform may read while executing."""

    def __init__(
        self,
        timestamp: Timestamp,
        quote: MarketQuote,
        position: PositionState,
        equity: Decimal = Decimal("0"),
        available_liquidity: Optional[Decimal] = None,
        currency: str = "USD",
    ) -> None:
        self._timestamp = timestamp
        self._quote = quote
        self._position = position
        self._equity = equity
        self._available_liquidity = available_liquidity
        self._currency = currency.strip().upper()

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def quote(self) -> MarketQuote:
        return self._quote

    @property
    def symbol(self) -> Symbol:
        return self._quote.symbol

    @property
    def position(self) -> PositionState:
        return self._position

    @property
    def equity(self) -> Decimal:
        return self._equity

    @property
    def available_liquidity(self) -> Optional[Decimal]:
        """Maximum executable size, or None when unconstrained."""
        return self._available_liquidity

    @property
    def currency(self) -> str:
        return self._currency
