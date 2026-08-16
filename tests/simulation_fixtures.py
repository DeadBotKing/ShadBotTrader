"""Shared candle builders for the simulation tests.

Lives at the tests root so both unit and integration suites can
import it without relative-package gymnastics.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Sequence

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)
XAU = Symbol("XAUUSD_i")
TF = Timeframe("5M")


def ts(minutes: int = 0) -> Timestamp:
    """A timestamp ``minutes`` after the base time."""
    return Timestamp(BASE_TIME + timedelta(minutes=minutes))


def make_candle(index: int, close: str, spread_pts: str = "3") -> Candle:
    """A candle at bar ``index`` closing at ``close``."""
    mid = Decimal(close)
    wing = Decimal(spread_pts)
    return Candle(
        symbol=XAU,
        timeframe=TF,
        open_time=ts(index * 5),
        open_price=Price(mid),
        high=Price(mid + wing),
        low=Price(mid - wing),
        close=Price(mid),
        volume=Decimal("100"),
    )


def candles_from(closes: Sequence[str]) -> List[Candle]:
    """Build a candle series from a list of close prices."""
    return [make_candle(index, close) for index, close in enumerate(closes)]


def rising(count: int = 20, start: int = 2000, step: int = 5) -> List[Candle]:
    """A monotonically rising series."""
    return candles_from([str(start + step * i) for i in range(count)])


def falling(count: int = 20, start: int = 2100, step: int = 5) -> List[Candle]:
    """A monotonically falling series."""
    return candles_from([str(start - step * i) for i in range(count)])


def flat_series(count: int = 20, price: int = 2000) -> List[Candle]:
    """A series that never moves."""
    return candles_from([str(price)] * count)
