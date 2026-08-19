"""Tests for Phase 29 forward labelling — with leakage as the main event.

Both targets look into the future by construction, which is precisely
where time-series projects leak. Phase 29 §4 states three rules; each
gets an explicit test here, because a leak produces a backtest that
looks excellent and a live account that loses money.
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.ai.prediction_target import SignalClass
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.target_builder import (
    align_to_labels,
    build_range_labels,
    build_signal_labels,
    build_signal_labels_from_candles,
    usable_row_count,
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


def series(closes):
    return [candle(index, close) for index, close in enumerate(closes)]


# --------------------------------------------------------------- range ---
class TestRangeLabels:
    def test_the_label_is_the_extreme_of_the_next_n_bars(self):
        candles = [
            candle(0, 100.0),
            candle(1, 101.0, high=105.0, low=99.0),
            candle(2, 102.0, high=103.0, low=95.0),
            candle(3, 100.0),
        ]
        labels = build_range_labels(candles, horizon=2)

        # row 0: window is bars 1-2 -> high 105, low 95, close 100
        assert labels.high_offset[0] == pytest.approx(0.05)
        assert labels.low_offset[0] == pytest.approx(-0.05)

    def test_r1_the_current_bar_never_contributes_to_its_own_label(self):
        """Bar 0 has an extreme high; it must not appear in bar 0's label."""
        candles = [
            candle(0, 100.0, high=999.0, low=1.0),  # absurd extremes
            candle(1, 100.0, high=101.0, low=99.0),
            candle(2, 100.0, high=101.0, low=99.0),
        ]
        labels = build_range_labels(candles, horizon=2)

        assert labels.high_offset[0] == pytest.approx(0.01)
        assert labels.low_offset[0] == pytest.approx(-0.01)

    def test_r2_the_final_rows_without_a_full_future_are_dropped(self):
        candles = series([100.0] * 20)
        labels = build_range_labels(candles, horizon=5)

        assert len(labels) == 15
        assert labels.source_index[-1] == 14  # never 15..19

    def test_a_series_shorter_than_the_horizon_is_refused(self):
        with pytest.raises(ValidationError):
            build_range_labels(series([100.0] * 3), horizon=5)

    def test_offsets_are_scale_free(self):
        """The same *shape* at a different price level yields equal labels.

        The wicks have to scale with the price too, otherwise the two
        series are not the same shape — which is exactly the property
        being asserted.
        """

        def proportional(closes):
            return [
                candle(index, close, high=close * 1.01, low=close * 0.99)
                for index, close in enumerate(closes)
            ]

        cheap = build_range_labels(proportional([100.0, 101.0, 102.0]), horizon=1)
        dear = build_range_labels(proportional([1000.0, 1010.0, 1020.0]), horizon=1)
        assert cheap.high_offset[0] == pytest.approx(dear.high_offset[0], rel=1e-9)
        assert cheap.low_offset[0] == pytest.approx(dear.low_offset[0], rel=1e-9)


# -------------------------------------------------------------- signal ---
class TestSignalLabels:
    def test_buy_is_the_first_future_threshold_hit(self):
        labels = build_signal_labels(
            series([100.0, 100.0, 100.01, 100.20]), horizon=0, threshold=0.001
        )
        assert labels.labels[0] == int(SignalClass.BUY)
        assert labels.source_index[0] == 0
        assert labels.hit_index[0] == 3
        assert labels.bars_to_hit[0] == 3

    def test_sell_is_the_reverse_first_passage(self):
        labels = build_signal_labels(
            series([100.0, 100.0, 99.99, 99.80]), horizon=0, threshold=0.001
        )
        assert labels.labels[0] == int(SignalClass.SELL)
        assert labels.hit_index[0] == 3

    def test_buy_is_rejected_when_a_future_low_breaks_the_start_low_first(self):
        candles = [
            candle(0, 100.0, high=101.0, low=99.0),
            candle(1, 101.0, high=102.0, low=98.0),
            candle(2, 101.0, high=103.0, low=100.0),
        ]
        labels = build_signal_labels_from_candles(candles, threshold=0.005)
        assert 0 not in labels.source_index

    def test_sell_is_rejected_when_a_future_high_breaks_the_start_high_first(self):
        candles = [
            candle(0, 100.0, high=101.0, low=99.0),
            candle(1, 99.0, high=102.0, low=98.0),
            candle(2, 99.0, high=100.0, low=97.0),
        ]
        labels = build_signal_labels_from_candles(candles, threshold=0.005)
        assert 0 not in labels.source_index

    def test_a_move_inside_the_old_band_has_no_label_until_a_barrier_hits(self):
        labels = build_signal_labels(series([100.0, 100.0, 100.01]), horizon=0, threshold=0.001)
        assert labels.is_empty

    def test_a_wider_threshold_changes_the_first_passage_time(self):
        closes = [100.0, 100.0, 100.5, 102.5]
        tight = build_signal_labels(series(closes), horizon=0, threshold=0.001)
        wide = build_signal_labels(series(closes), horizon=0, threshold=0.02)
        assert tight.labels[0] == int(SignalClass.BUY)
        assert wide.labels[0] == int(SignalClass.BUY)
        assert tight.bars_to_hit[0] < wide.bars_to_hit[0]

    def test_unbounded_search_drops_starts_that_never_hit_a_barrier(self):
        labels = build_signal_labels(series([100.0] * 20), horizon=0, threshold=0.001)
        assert labels.is_empty
        assert labels.distribution() == {"sell": 0, "buy": 0}
        assert labels.is_degenerate()

    def test_a_series_with_both_binary_classes_is_not_degenerate(self):
        closes = []
        price = 100.0
        for index in range(90):
            phase = index % 2
            price *= 1.01 if phase == 0 else 0.99
            closes.append(price)

        labels = build_signal_labels(series(closes), horizon=0, threshold=0.002)
        distribution = labels.distribution()
        assert distribution["buy"] > 0
        assert distribution["sell"] > 0
        assert set(distribution) == {"sell", "buy"}
        assert not labels.is_degenerate()

    def test_the_forward_return_and_hit_metadata_are_kept_for_auditing(self):
        labels = build_signal_labels(series([100.0, 100.0, 110.0]), horizon=0, threshold=0.001)
        assert labels.forward_return[0] == pytest.approx(0.10)
        assert labels.hit_index[0] == 2
        assert labels.bars_to_hit[0] == 2

    def test_a_non_positive_threshold_is_refused(self):
        with pytest.raises(ValidationError):
            build_signal_labels(series([100.0] * 10), horizon=0, threshold=0.0)


# ------------------------------------------------------------ alignment ---
class TestAlignment:
    def test_usable_rows_shrink_by_exactly_the_horizon(self):
        assert usable_row_count(100, 5) == 95
        assert usable_row_count(3, 5) == 0

    def test_rows_are_matched_to_labels_by_candle_index(self):
        """Features drop rows at the start, labels at the end."""
        rows = [[float(index)] for index in range(10)]
        aligned, kept = align_to_labels(rows, source_index=[2, 3, 4])

        assert aligned == [[2.0], [3.0], [4.0]]
        assert kept == [0, 1, 2]

    def test_a_label_without_a_feature_row_is_skipped(self):
        rows = [[0.0], [1.0]]
        aligned, kept = align_to_labels(rows, source_index=[0, 1, 7])

        assert len(aligned) == 2
        assert kept == [0, 1]
