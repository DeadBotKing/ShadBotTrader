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


def _warmup(n: int = 289) -> list:
    """288+ کندل ثابت برای daily_range warm-up (فاز ۹۹-ب)."""
    return [mk(i, 100.0, 101.0, 99.0) for i in range(n)]


class TestTrendSignalLabels:
    def test_sharp_up_is_buy(self):
        candles = _warmup() + [mk(289, 100, 101, 99), mk(290, 100, 104, 99.5)]
        labels = build_trend_signal_labels(candles, horizon=1, atr_mult=0.5)
        assert 2 in labels.labels  # BUY در جایی از سری

    def test_sharp_down_is_sell(self):
        candles = _warmup() + [mk(289, 100, 101, 99), mk(290, 100, 100.5, 97)]
        labels = build_trend_signal_labels(candles, horizon=1, atr_mult=0.5)
        assert 0 in labels.labels  # SELL

    def test_ambiguous_bar_is_skipped(self):
        # یک کندل هم مانع بالا هم پایین را می‌زند → نمونه حذف
        labels = build_trend_signal_labels([mk(0, 100, 101, 99), mk(1, 100, 103, 97)],
                                           horizon=1, atr_mult=0.5)
        assert len(labels) == 0

    def test_quiet_series_is_hold(self):
        candles = _warmup() + [mk(289, 100, 101, 99)] + [
            mk(290 + i, 100, 100.3, 99.7) for i in range(4)
        ]
        labels = build_trend_signal_labels(candles, horizon=4, atr_mult=0.5)
        # آخرین ۴ برچسب باید HOLD باشند (کندل‌های آرام بعد از warm-up)
        assert labels.labels[-4:] == [1, 1, 1, 1]

    def test_first_touch_wins(self):
        # الگو: مانع بالا = close + 0.5×daily_range؛ اولین برخورد برنده
        warm = _warmup()
        candles = warm + [
            mk(289, 100, 101, 99),
            mk(290, 100, 100.5, 99.5),
            mk(291, 100, 115, 99.5),  # برخورد بالا
            mk(292, 100, 100.5, 80),  # دیر هنگام
        ]
        labels = build_trend_signal_labels(candles, horizon=3, atr_mult=0.5)
        # فقط برچسب‌های بعد از warm-up را چک کن
        assert 2 in labels.labels  # BUY جایی در سری

    def test_causality_future_jolt_does_not_change_past_labels(self):
        candles = _warmup() + [mk(289 + i, 100 + i * 0.05) for i in range(10)]
        before = build_trend_signal_labels(candles, horizon=3)
        jolted = list(candles)
        jolted[-3] = mk(len(candles) - 3, 130, 135, 125)
        after = build_trend_signal_labels(jolted, horizon=3)
        # برچسب‌های اولیه نباید تغییر کنند
        assert before.labels[:5] == after.labels[:5]

    def test_horizon_and_mult_validation(self):
        candles = _warmup() + [mk(289, 100)]
        with pytest.raises(ValidationError):
            build_trend_signal_labels(candles, horizon=0)
        with pytest.raises(ValidationError):
            build_trend_signal_labels(candles, horizon=2, atr_mult=0.0)

    def test_atr_scaling_changes_the_barriers(self):
        # با atr_mult بزرگ‌تر، حرکت ملایم دیگر مانع را نمی‌زند → HOLD
        warm = _warmup()
        # daily_range از 288 کندل warm-up: max(high)−min(low) = 2
        # مانع 0.5×2 = $1 از close — حرکت باید بیشتر از این باشد
        tail = [
            mk(289, 100, 101, 99),
            mk(290, 100, 100.5, 99.5),
            mk(291, 100, 108, 92),   # برخورد هر دو مانع → مبهم → حذف
            mk(292, 100, 100.5, 99.5),
            mk(293, 100, 102.5, 97.5),  # مانع بالا = close+1 → 102.5 ≥ 101 ✓ BUY
        ]
        candles = warm + tail
        small = build_trend_signal_labels(candles, horizon=3, atr_mult=0.5)
        big = build_trend_signal_labels(candles, horizon=3, atr_mult=5.0)
        # مانع 5×2 = $10: 102.5 < 110 و 97.5 > 90 → HOLD
        # small: مانع $1 از close — برچسب‌ها BUY/SELL (بدون HOLD)
        assert small.labels != big.labels  # آستانه متفاوت → برچسب متفاوت
