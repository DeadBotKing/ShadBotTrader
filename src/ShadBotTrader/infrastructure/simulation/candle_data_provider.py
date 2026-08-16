"""Historical candle data provider for simulations (Phase 16, §14-15).

Wraps a candle series behind ``SimulationMarketDataProvider`` so the
engine never learns where the data came from. Quotes are derived from
each candle's close with a configured spread.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.execution.market_view import MarketQuote
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.domain.simulation.ports import SimulationMarketDataProvider


class CandleMarketDataProvider(SimulationMarketDataProvider):
    """Replays a candle series as market events.

    Candles are sorted by open time on construction, so the engine can
    rely on chronological delivery regardless of how the caller stored
    them.
    """

    def __init__(
        self,
        symbol: Symbol,
        candles: Sequence[Candle],
        spread: Decimal = Decimal("2"),
    ) -> None:
        if spread < 0:
            raise ValidationError("spread must not be negative")
        self._symbol = symbol
        self._candles: List[Candle] = sorted(candles, key=lambda c: c.open_time.value)
        self._spread = spread
        self._by_time: Dict[object, Candle] = {
            candle.open_time.value: candle for candle in self._candles
        }

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def candles(self) -> List[Candle]:
        return list(self._candles)

    def events(self) -> List[MarketEvent]:
        """Every candle as a market event, in chronological order."""
        return [MarketEvent.from_candle(self._symbol, candle) for candle in self._candles]

    def quote_at(self, symbol: Symbol, moment: Timestamp) -> Optional[MarketQuote]:
        """Build the quote implied by the candle at ``moment``."""
        if symbol != self._symbol:
            return None
        candle = self._by_time.get(moment.value)
        if candle is None:
            return None
        return self.quote_for(candle)

    def quote_for(self, candle: Candle) -> MarketQuote:
        """Derive a symmetric quote around a candle's close."""
        return MarketQuote.from_mid(
            symbol=self._symbol,
            mid=candle.close,
            spread=self._spread,
            timestamp=candle.open_time,
        )
