"""باگ ۵۰ — بافر 1D باید از تاریخچهٔ قبل از شروع replay پیش‌پر شود.

ریشه: ``DualModelPredictionSource`` بافر 1D را فقط با ``observe`` پر می‌کرد؛
یعنی برای اینکه اولین رنج تولید شود باید *در طول خود replay* ۱۵۰ روزِ
دیگر هم می‌گذشت (بافر شروع = صفر). اجرای کاربر با ۹٬۰۰۰ کندل 5M (~۳۱ روز)
هرگز به آن نمی‌رسید → رنج همیشه abstain → همهٔ نقاط سیگنال بدون TP/SL.

قفل‌ها:
1. کندل‌های 1D بسته‌شدهٔ قبل از اولین کندل 5M از ابتدا در بافرند.
2. بعد از feed کوتاه 5M، رنج واقعاً پیش‌بینی می‌شود (نه abstain).
3. cursor پیش رفته تا observe دوباره اضافه نکند (بدون تکرار).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.market_event import MarketEvent, MarketEventType
from ShadBotTrader.infrastructure.simulation.dual_model_prediction_source import (
    DualModelPredictionSource,
)

SYMBOL = Symbol("XAUUSD")
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)
FIVE_M = Timeframe("5M")
ONE_D = Timeframe("1D")


def _candle(hours: float, tf: Timeframe) -> Candle:
    return Candle(
        symbol=SYMBOL,
        timeframe=tf,
        open_time=Timestamp(BASE + timedelta(hours=hours)),
        open_price=Price(Decimal("2000")),
        high=Price(Decimal("2001")),
        low=Price(Decimal("1999")),
        close=Price(Decimal("2000")),
        volume=Decimal("10"),
    )


def _source(daily_history_days: int):
    """سری 5M از روز ۴۰۰ شروع می‌شود؛ تاریخچهٔ 1D از روز ۰ موجود است."""
    signal_candles = [_candle(400 * 24 + i / 12, FIVE_M) for i in range(400)]
    range_candles = [_candle(float(i), ONE_D) for i in range(400 + daily_history_days)]

    class _FakeSignal:
        def forecast(self, artifact, window, generated_at=""):
            return SignalForecast.from_vector((0.2, 0.8), horizon=0, timeframe="5M")

    class _FakeRange:
        def forecast(self, artifact, window, reference_close=0.0, generated_at=""):
            return RangeForecast(
                reference_close=2000.0,
                high_offset=0.006,
                low_offset=-0.005,
                horizon=1,
                timeframe="1D",
            )

    return DualModelPredictionSource(
        signal_artifact=object(),
        signal_predictor=_FakeSignal(),
        range_artifact=object(),
        range_predictor=_FakeRange(),
        symbol=SYMBOL,
        signal_timeframe=FIVE_M,
        range_timeframe=ONE_D,
        range_candles=range_candles,
        signal_candles=signal_candles,
        signal_window_size=150,
        range_window_size=150,
        min_signal_confidence=0.6,
    )


def test_history_before_replay_pre_fills_the_buffer():
    source = _source(daily_history_days=370)
    # ۳۷۰ روز قبل از شروع 5M بسته شده‌اند → باید از اول در بافر باشند
    assert len(source._range_candles) >= 150
    # cursor باید جلو رفته باشد تا observe دوباره همان‌ها را اضافه نکند


def test_short_replay_still_produces_range_forecasts():
    """فاجعهٔ قبل: ۳۰۰×5M = ۱ روز replay — رنج باید از اول کار کند."""
    source = _source(daily_history_days=370)
    for i in range(300):
        event = MarketEvent(
            event_type=MarketEventType.CANDLE,
            symbol=SYMBOL,
            event_time=Timestamp(BASE + timedelta(hours=400 * 24) + timedelta(minutes=5 * (i + 1))),
            candle=_candle(400 * 24 + (i + 1) / 12, FIVE_M),
        )
        source.observe(event)
        source.predict(event)

    stats = source.stats()
    assert (
        stats["range_predictions"] > 0
    ), "range must be predictable from the very first actionable signal"
    forecast = source.last_range_forecast
    assert forecast is not None
    assert forecast.predicted_high == 2012.0
    assert forecast.predicted_low == 1990.0
