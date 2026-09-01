"""فاز ۹۶-ب — فیلتر ترند EMA50 روزانه در منبع پیش‌بینی.

دو دیتاست بکتست نشان دادند ضرر اصلی short-در-روند-صعودی است (ران
آخر: 142 short از 175!). فیلتر ``ema50`` ورودِ خلاف ترند روزانه را در
منبع رد می‌کند — قبل از مصرف مدل رنج — و بلوک‌ها را در stats می‌شمارد.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.infrastructure.simulation.dual_model_prediction_source import (
    DualModelPredictionSource,
)

SYMBOL = Symbol("XAUUSD")
TF = Timeframe("1D")
BASE = datetime(2026, 1, 5, tzinfo=timezone.utc)


class _TrendCandle(Candle):
    """کندل با close کنترل‌شده (high/low = close ± 1)."""

    @classmethod
    def make(cls, index: int, close: float) -> Candle:
        return Candle(
            symbol=SYMBOL,
            timeframe=TF,
            open_time=Timestamp(BASE + timedelta(days=index)),
            open_price=Price(Decimal(str(close))),
            high=Price(Decimal(str(close + 1))),
            low=Price(Decimal(str(close - 1))),
            close=Price(Decimal(str(close))),
            volume=Decimal("100"),
        )


class _SidePredictor:
    """همیشه یک جهت با اطمینان 0.9 برمی‌گرداند."""

    def __init__(self, side: str) -> None:
        self._side = side

    def forecast(self, artifact, window, generated_at=""):
        from ShadBotTrader.domain.ai.prediction_target import SignalForecast

        vector = (0.9, 0.1) if self._side == "sell" else (0.1, 0.9)
        return SignalForecast.from_vector(vector, horizon=1, timeframe="1H")


class _NullRangePredictor:
    def __init__(self) -> None:
        self.calls = 0

    def forecast(self, artifact, window, reference_close, generated_at="", **_):
        self.calls += 1
        from ShadBotTrader.domain.ai.prediction_target import RangeForecast

        return RangeForecast(
            reference_close=reference_close,
            high_offset=0.01,
            low_offset=-0.01,
            horizon=1,
            timeframe="1D",
        )


class _StubMatrix:
    def __init__(self, rows: int) -> None:
        self.rows = [[0.0] * 3 for _ in range(rows)]
        self.source_index = list(range(rows))


def _source(closes, side, trend_filter):
    candles = [_TrendCandle.make(i, c) for i, c in enumerate(closes)]
    rows = max(len(candles), 4)
    range_predictor = _NullRangePredictor()
    source = DualModelPredictionSource(
        signal_artifact=None,
        signal_predictor=_SidePredictor(side),
        range_artifact=object(),
        range_predictor=range_predictor,
        symbol=SYMBOL,
        signal_timeframe=Timeframe("1D"),
        range_timeframe=TF,
        range_candles=candles,
        signal_window_size=2,
        range_window_size=2,
        signal_matrix=_StubMatrix(rows),
        range_matrix=_StubMatrix(rows),
        signal_candles=candles,
        range_target_units="atr",
        trend_filter=trend_filter,
    )
    for candle in candles:
        source.observe(MarketEvent.from_candle(SYMBOL, candle))
    return source, range_predictor


def _last(candles):
    return candles[-1]


class TestEma50TrendFilter:
    CLOSES_UPTREND = [2000.0 + 6.0 * i for i in range(120)]  # صعودی تند

    def test_unknown_filter_is_refused(self):
        with pytest.raises(ValidationError):
            _source(self.CLOSES_UPTREND, "sell", "macd")  # noqa: B015

    def test_short_blocked_in_uptrend(self):
        source, range_predictor = _source(self.CLOSES_UPTREND, "sell", "ema50")
        source.predict(MarketEvent.from_candle(SYMBOL, _last_candle(self.CLOSES_UPTREND)))
        stats = source.stats()
        assert stats["trend_blocked"] == 1
        assert range_predictor.calls == 0  # قبل از مصرف مدل رنج رد شده
        assert stats["trend_filter"] == "ema50"

    def test_short_allowed_in_downtrend(self):
        closes = [3000.0 - 6.0 * i for i in range(120)]
        source, range_predictor = _source(closes, "sell", "ema50")
        source.predict(MarketEvent.from_candle(SYMBOL, _last_candle(closes)))
        assert source.stats()["trend_blocked"] == 0
        assert range_predictor.calls == 1

    def test_long_blocked_in_downtrend(self):
        closes = [3000.0 - 6.0 * i for i in range(120)]
        source, range_predictor = _source(closes, "buy", "ema50")
        source.predict(MarketEvent.from_candle(SYMBOL, _last_candle(closes)))
        assert source.stats()["trend_blocked"] == 1
        assert range_predictor.calls == 0

    def test_filter_off_never_blocks(self):
        source, range_predictor = _source(self.CLOSES_UPTREND, "sell", "none")
        source.predict(MarketEvent.from_candle(SYMBOL, _last_candle(self.CLOSES_UPTREND)))
        assert source.stats()["trend_blocked"] == 0
        assert range_predictor.calls == 1

    def test_short_history_disables_the_filter(self):
        closes = self.CLOSES_UPTREND[:30]  # < دورهٔ ۵۰
        source, range_predictor = _source(closes, "sell", "ema50")
        source.predict(MarketEvent.from_candle(SYMBOL, _last_candle(closes)))
        assert source.stats()["trend_blocked"] == 0
        assert range_predictor.calls == 1


def _last_candle(closes):
    return _TrendCandle.make(len(closes) - 1, closes[-1])
