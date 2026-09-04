"""فاز ۹۹ — برچسب‌ساز سیگنال ترند (سه‌کلاسه BUY/HOLD/SELL).

برای هر کندل تصمیم t: در افق (پیش‌فرض 288 کندل) اولین برخورد
قیمت با مانع ±X×ATR14 → BUY/SELL؛ بدون برخورد → HOLD؛
برخورد هر دو مانع در یک کندل → نمونهٔ مبهم حذف.
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
from ShadBotTrader.infrastructure.ai.target_builder import build_trend_signal_labels

SYMBOL = Symbol("XAUUSD")
TF = Timeframe("5M")
BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def mk(i: int, close: float, high: float | None = None, low: float | None = None) -> Candle:
    high = close + 1 if high is None else high
    low = close - 1 if low is None else low
    return Candle(
        symbol=SYMBOL,
        timeframe=TF,
        open_time=Timestamp(BASE + timedelta(minutes=5 * i)),
        open_price=Price(Decimal(str(close))),
        high=Price(Decimal(str(high))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(close))),
        volume=Decimal("1"),
    )


class TestTrendSignalLabels:
    def test_sharp_up_is_buy(self):
        labels = build_trend_signal_labels([mk(0, 100, 101, 99), mk(1, 100, 104, 99.5)],
                                           horizon=1, atr_mult=0.5)
        assert labels.labels == [2]  # BUY
        assert labels.distribution()["buy"] == 1

    def test_sharp_down_is_sell(self):
        labels = build_trend_signal_labels([mk(0, 100, 101, 99), mk(1, 100, 100.5, 97)],
                                           horizon=1, atr_mult=0.5)
        assert labels.labels == [0]  # SELL

    def test_ambiguous_bar_is_skipped(self):
        # یک کندل هم مانع بالا هم پایین را می‌زند → نمونه حذف
        labels = build_trend_signal_labels([mk(0, 100, 101, 99), mk(1, 100, 103, 97)],
                                           horizon=1, atr_mult=0.5)
        assert len(labels) == 0

    def test_quiet_series_is_hold(self):
        candles = [mk(0, 100, 101, 99)] + [mk(i, 100, 100.3, 99.7) for i in range(1, 5)]
        labels = build_trend_signal_labels(candles, horizon=4, atr_mult=0.5)
        assert labels.labels == [1, 1, 1, 1]  # همه HOLD
        assert labels.distribution()["hold"] == 4

    def test_first_touch_wins(self):
        # t=0: مانع بالا=101؛ کندل 2 (high=104) اولین برخورد → BUY
        # t=1: مانع بالا=100.75؛ کندل 2 دوباره اولین → BUY
        # t=2: مانع پایین=98.75؛ کندل 3 (low=90) → SELL
        candles = [
            mk(0, 100, 101, 99),
            mk(1, 100, 100.5, 99.5),
            mk(2, 100, 104, 99.5),
            mk(3, 100, 100.5, 90),
        ]
        labels = build_trend_signal_labels(candles, horizon=3, atr_mult=0.5)
        assert labels.labels == [2, 2, 0]
        assert labels.label_end_index == [2, 2, 3]

    def test_causality_future_jolt_does_not_change_past_labels(self):
        candles = [mk(i, 100 + i * 0.05) for i in range(10)]
        before = build_trend_signal_labels(candles, horizon=3)
        jolted = list(candles)
        jolted[8] = mk(8, 130, 135, 125)
        after = build_trend_signal_labels(jolted, horizon=3)
        assert before.labels[:3] == after.labels[:3]

    def test_horizon_and_mult_validation(self):
        candles = [mk(i, 100) for i in range(6)]
        with pytest.raises(ValidationError):
            build_trend_signal_labels(candles, horizon=0)
        with pytest.raises(ValidationError):
            build_trend_signal_labels(candles, horizon=2, atr_mult=0.0)

    def test_atr_scaling_changes_the_barriers(self):
        # با atr_mult بزرگ‌تر، حرکت ملایم دیگر مانع را نمی‌زند → HOLD
        # (low کندل 1 = 99.5 بالای مانع پایین 99 — فقط مانع بالا لمس می‌شود)
        candles = [mk(0, 100, 101, 99), mk(1, 100, 102.2, 99.5), mk(2, 100, 100.4, 99.6)]
        small = build_trend_signal_labels(candles, horizon=1, atr_mult=0.5)
        big = build_trend_signal_labels(candles, horizon=1, atr_mult=5.0)
        # t=0: ATR=2 → مانع بالا 101؛ high کندل 1 = 102.2 ≥ 101 → BUY
        assert small.labels[0] == 2
        # t=0 با مانع 110: 102.2 < 110 و 99.5 > 90 → HOLD
        assert big.labels[0] == 1
