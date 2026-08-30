"""فاز ۹۵ — ATR-normalized range targets.

The pct target made the range model answer one constant percentage for
every candle (see ``docs/Report/RANGE_MODEL_CONSTANT_OFFSET_ROOT_CAUSE.md``).
The fix: labels are ATR multiples, ``(future − close) / ATR14[t]``, and
the predictor de-normalizes them with the same ATR definition.

These tests pin the three invariants that make that contract sound:

1. the ATR series itself (hand-computed Wilder values, causal);
2. the labels (exact ATR multiples, leakage-free, unit-tagged);
3. the round trip (label × ATR recreates the dollar distance).
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
from ShadBotTrader.infrastructure.ai.target_builder import (
    atr_from_candles,
    build_range_labels,
    build_range_labels_seq2seq,
    wilder_atr_series,
)

SYMBOL = Symbol("XAUUSD")
TF = Timeframe("1H")
BASE = datetime(2026, 1, 5, tzinfo=timezone.utc)


def candle(index: int, close: float, high: float | None = None, low: float | None = None):
    high = close + 1 if high is None else high
    low = close - 1 if low is None else low
    return Candle(
        symbol=SYMBOL,
        timeframe=TF,
        open_time=Timestamp(BASE + timedelta(hours=index)),
        open_price=Price(Decimal(str(close))),
        high=Price(Decimal(str(high))),
        low=Price(Decimal(str(low))),
        close=Price(Decimal(str(close))),
        volume=Decimal("100"),
    )


# ------------------------------------------------------- wilder ATR ----
class TestWilderAtrSeries:
    def test_expanding_mean_seed_then_wilder_smoothing(self):
        # TR[0]=2 (high-low). TR[1]=max(2, |101-100|, |99-100|)=2? use
        # explicit numbers: candle i: high=close+1, low=close-1, closes
        # rise by 1 → TR = max(2, 2, 0) = 2 every bar → ATR stays 2.
        closes = [100.0 + index for index in range(20)]
        highs = [close + 1 for close in closes]
        lows = [close - 1 for close in closes]
        atr = wilder_atr_series(highs, lows, closes, period=14)
        assert len(atr) == 20
        assert all(value == pytest.approx(2.0) for value in atr)

    def test_wilder_smoothing_pulls_toward_the_new_tr(self):
        # A constant-TR series jolted by one big range: after the jolt the
        # ATR must decay geometrically (period=4 → factor 3/4 per bar).
        closes = [100.0] * 12
        highs = [101.0] * 12
        lows = [99.0] * 12
        highs[6] = 111.0  # TR jumps from 2 to 11 + gaps? closes equal → TR=12
        atr = wilder_atr_series(highs, lows, closes, period=4)
        # before the jolt: TR=2 everywhere → ATR=2
        assert atr[5] == pytest.approx(2.0)
        # jolt bar: TR = 111-99 = 12 → expanding seed done (index>=4):
        # atr = (2*3 + 12)/4 = 4.5
        assert atr[6] == pytest.approx((2.0 * 3 + 12.0) / 4.0)
        # next bar: TR back to 2 → atr = (4.5*3 + 2)/4 = 3.875
        assert atr[7] == pytest.approx((4.5 * 3 + 2.0) / 4.0)

    def test_is_causal_slice_invariance(self):
        """ATR at index t must not move when future candles appear."""
        closes = [100.0 + (index % 5) for index in range(30)]
        highs = [close + 1.5 for close in closes]
        lows = [close - 1.5 for close in closes]
        prefix = wilder_atr_series(highs[:20], lows[:20], closes[:20], period=14)
        full = wilder_atr_series(highs, lows, closes, period=14)
        assert prefix == pytest.approx(full[:20])

    def test_mismatched_series_are_refused(self):
        with pytest.raises(ValidationError):
            wilder_atr_series([1.0, 2.0], [1.0], [1.0, 2.0], period=14)

    def test_atr_from_candles_matches_series_tail(self):
        candles = [candle(index, 100.0 + index * 0.5) for index in range(30)]
        highs = [float(c.high.amount) for c in candles]
        lows = [float(c.low.amount) for c in candles]
        closes = [float(c.close.amount) for c in candles]
        series = wilder_atr_series(highs, lows, closes, period=14)
        assert atr_from_candles(candles, period=14) == pytest.approx(series[-1])
        assert atr_from_candles([], period=14) is None


# ----------------------------------------------------- ATR labels ------
class TestAtrRangeLabels:
    def test_default_units_are_atr(self):
        candles = [candle(index, 100.0 + index) for index in range(30)]
        labels = build_range_labels(candles, horizon=3)
        assert labels.units == "atr"

    def test_label_is_an_atr_multiple(self):
        # closes rise by 2 every bar; high=close+2, low=close-2 → TR=4?
        # TR[t] = max(4, |high-prev_close|=3, |low-prev_close|=3) → 4.
        candles = [
            candle(index, 100.0 + 2 * index, high=102.0 + 2 * index, low=98.0 + 2 * index)
            for index in range(30)
        ]
        labels = build_range_labels(candles, horizon=1, units="atr", atr_period=14)
        highs = [float(c.high.amount) for c in candles]
        lows = [float(c.low.amount) for c in candles]
        closes = [float(c.close.amount) for c in candles]
        atr = wilder_atr_series(highs, lows, closes, period=14)
        # label[t] = (high[t+1] − close[t]) / ATR[t]
        for t in (0, 5, 15, 28):
            expected = (highs[t + 1] - closes[t]) / atr[t]
            assert labels.high_offset[t] == pytest.approx(expected)
            assert labels.low_offset[t] == pytest.approx((lows[t + 1] - closes[t]) / atr[t])

    def test_round_trip_recreates_dollar_distance(self):
        """label × ATR[t] must equal the dollar distance the label encoded."""
        candles = [candle(index, 2000.0 + index * 3.0) for index in range(30)]
        labels = build_range_labels(candles, horizon=1)
        highs = [float(c.high.amount) for c in candles]
        lows = [float(c.low.amount) for c in candles]
        closes = [float(c.close.amount) for c in candles]
        atr_series = wilder_atr_series(highs, lows, closes, period=14)
        atr0 = atr_series[0]
        # ATR at candle 0 from a causal one-candle slice must agree
        assert atr_from_candles(candles[:1], period=14) == pytest.approx(atr0)
        assert labels.high_offset[0] * atr0 == pytest.approx(highs[1] - closes[0])
        assert labels.low_offset[0] * atr0 == pytest.approx(lows[1] - closes[0])

    def test_future_beyond_the_horizon_cannot_leak(self):
        candles = [candle(index, 100.0 + index) for index in range(20)]
        baseline = build_range_labels(candles, horizon=2)
        candles[10] = candle(10, 500.0, high=900.0, low=50.0)  # far future jolt
        perturbed = build_range_labels(candles, horizon=2)
        assert baseline.high_offset[0] == pytest.approx(perturbed.high_offset[0])
        assert baseline.low_offset[0] == pytest.approx(perturbed.low_offset[0])

    def test_flat_series_is_refused_not_zero_divided(self):
        candles = [candle(index, 100.0, high=100.0, low=100.0) for index in range(20)]
        with pytest.raises(ValidationError):
            build_range_labels(candles, horizon=2, units="atr")

    def test_unknown_units_are_refused(self):
        candles = [candle(index, 100.0 + index) for index in range(10)]
        with pytest.raises(ValidationError):
            build_range_labels(candles, horizon=2, units="dollars")
        with pytest.raises(ValidationError):
            build_range_labels_seq2seq(candles, horizon=2, units="dollars")


class TestAtrSeq2SeqLabels:
    def test_units_and_values(self):
        candles = [
            candle(index, 100.0 + 2 * index, high=102.0 + 2 * index, low=98.0 + 2 * index)
            for index in range(30)
        ]
        labels = build_range_labels_seq2seq(candles, horizon=3)
        assert labels.units == "atr"
        highs = [float(c.high.amount) for c in candles]
        lows = [float(c.low.amount) for c in candles]
        closes = [float(c.close.amount) for c in candles]
        atr = wilder_atr_series(highs, lows, closes, period=14)
        assert len(labels) == len(candles) - 3
        # row t, step k uses the SAME ATR[t] for high and low
        t, k = 7, 2
        assert labels.high_seq[t][k] == pytest.approx((highs[t + k + 1] - closes[t]) / atr[t])
        assert labels.low_seq[t][k] == pytest.approx((lows[t + k + 1] - closes[t]) / atr[t])

    def test_flat_targets_keep_the_interleaved_layout(self):
        candles = [candle(index, 100.0 + index) for index in range(10)]
        labels = build_range_labels_seq2seq(candles, horizon=2, units="pct")
        flat = labels.to_flat_targets()[0]
        assert flat == [
            labels.high_seq[0][0],
            labels.low_seq[0][0],
            labels.high_seq[0][1],
            labels.low_seq[0][1],
        ]
