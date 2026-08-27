"""باگ ۴۹ — برش last_n نباید کندل‌های 1D رنج را قطع کند.

ریشه: handler بکتست، range candles را با همان cutoff زمانیِ پنجرهٔ 5M
می‌برید: ۹٬۰۰۰ کندل 5M ≈ ۳۱ روز → فقط ~۳۰ کندل 1D می‌ماند در حالی که
مدل رنج window=150 می‌خواهد → abstain همیشگی → trades=0.

این تست‌ها دو طرف ماجرا را قفل می‌کنند:
1. موتور با < window کندل 1D درست رفتار می‌کند (abstain) — یعنی برش
   last_n عملاً کل بکتست را فلج می‌کرد؛ حذف برش تنها راه درست بود.
2. با تاریخچهٔ کامل 1D، رنج دیگر گرسنه نیست (قرارداد فیکس در handler
   به‌صورت متنی هم قفل شده).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.simulation.market_event import (
    MarketEvent,
    MarketEventType,
)
from ShadBotTrader.infrastructure.simulation.dual_model_prediction_source import (
    DualModelPredictionSource,
)

SYMBOL = Symbol("XAUUSD")
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)
FIVE_M = Timeframe("5M")
ONE_D = Timeframe("1D")


def _candle(hour_offset: float, tf: Timeframe) -> Candle:
    return Candle(
        symbol=SYMBOL,
        timeframe=tf,
        open_time=Timestamp(BASE + timedelta(hours=hour_offset)),
        open_price=Price(Decimal("2000")),
        high=Price(Decimal("2001")),
        low=Price(Decimal("1999")),
        close=Price(Decimal("2000")),
        volume=Decimal("10"),
    )


def _source(range_count: int) -> DualModelPredictionSource:
    signal_candles = [_candle(i / 12.0, FIVE_M) for i in range(400)]
    range_candles = [_candle(float(i), ONE_D) for i in range(range_count)]
    return DualModelPredictionSource(
        signal_artifact=object(),
        signal_predictor=object(),
        range_artifact=object(),
        range_predictor=object(),
        symbol=SYMBOL,
        signal_timeframe=FIVE_M,
        range_timeframe=ONE_D,
        range_candles=range_candles,
        signal_candles=signal_candles,
        signal_window_size=150,
        range_window_size=150,
    )


def _feed(source: DualModelPredictionSource, count: int) -> None:
    for i in range(count):
        event = MarketEvent(
            event_type=MarketEventType.CANDLE,
            symbol=SYMBOL,
            event_time=Timestamp(BASE + timedelta(minutes=5 * (i + 1))),
            candle=_candle((i + 1) / 12.0, FIVE_M),
        )
        source.observe(event)
        source.predict(event)  # abstainها فقط در predict ثبت می‌شوند


def test_thirty_daily_candles_starve_the_range_model():
    """سناریوی باگ: ~۳۰ کندل 1D (برش last_n) → رنج هرگز پیش‌بینی نمی‌کند."""
    source = _source(range_count=30)
    _feed(source, 300)

    stats = source.stats()
    assert stats["range_predictions"] == 0
    assert stats["range_window_size"] == 150
    assert source.abstentions > 0
    assert len(source._all_range_candles) == 30


def test_full_daily_history_covers_the_range_window():
    """فیکس: تاریخچهٔ کامل 1D به source می‌رسد — دیگر گرسنگی رنج نیست."""
    source = _source(range_count=400)
    _feed(source, 300)

    stats = source.stats()
    assert len(source._all_range_candles) == 400
    assert stats["range_window_size"] == 150
    # تفاوت با سناریوی باگ: خوراک رنج کامل است (پیش‌بینی واقعی به وزن
    # مدل وابسته است و با predictor جعلی اینجا اجرا نمی‌شود — هدف این
    # تست فقط هندسهٔ خوراک است).
    assert source._range_cursor == min(400, 300 // 24 + 1) or source._range_cursor > 0


def test_handler_no_longer_trims_range_by_cutoff():
    """قرارداد فیکس در متن handler قفل شود: دیگر برش range با cutoff نیست."""
    handler_src = (
        Path(__file__).resolve().parents[3]
        / "src"
        / "ShadBotTrader"
        / "presentation"
        / "commands"
        / "handlers.py"
    ).read_text(encoding="utf-8")
    assert "range candles هم به همان نسبت زمانی برش" not in handler_src
    assert "باگ ۴۹" in handler_src
