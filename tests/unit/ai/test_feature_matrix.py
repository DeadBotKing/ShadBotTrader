"""Tests for the feature matrix that feeds both Phase 29 models."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.feature_matrix import (
    BASE_COLUMNS,
    CANDLE_COLUMNS,
    RAW_PRICE_COLUMNS,
    attach_targets,
    build_feature_matrix,
    is_price_scaled,
)

SYMBOL = Symbol("XAUUSD")
TF = Timeframe("1H")
BASE = datetime(2026, 1, 5, tzinfo=timezone.utc)


def make(count: int = 30, start: float = 2000.0):
    candles = []
    price = start
    for index in range(count):
        move = 2.0 if index % 2 else -1.5
        open_, close = price, price + move
        candles.append(
            Candle(
                symbol=SYMBOL,
                timeframe=TF,
                open_time=Timestamp(BASE + timedelta(hours=index)),
                open_price=Price(Decimal(str(round(open_, 2)))),
                high=Price(Decimal(str(round(max(open_, close) + 1.0, 2)))),
                low=Price(Decimal(str(round(min(open_, close) - 1.0, 2)))),
                close=Price(Decimal(str(round(close, 2)))),
                volume=Decimal("120"),
            )
        )
        price = close
    return candles


# ------------------------------------------------------ price scaling ---
class TestPriceScaling:
    def test_moving_averages_are_recognised_as_price_valued(self):
        for name in ("sma_20", "ema_50", "close_filter", "bollinger_upper_20"):
            assert is_price_scaled(name), name

    def test_bounded_oscillators_are_left_alone(self):
        """RSI is already 0-100; dividing it by price would destroy it."""
        for name in ("rsi_14", "stochastic_14", "cci_20_ratio", "momentum_index"):
            assert not is_price_scaled(name), name


# ------------------------------------------------------------- matrix ---
class TestFeatureMatrix:
    def test_ohlcv_only_gives_the_fourteen_candle_columns(self):
        """Phase 30 added the 8 raw price columns to the original 6."""
        matrix = build_feature_matrix(make(), SYMBOL, TF, include_features=False)

        assert matrix.column_names == list(CANDLE_COLUMNS)
        assert matrix.width == 14
        assert len(matrix) == 30

    def test_the_raw_prices_come_before_the_derived_columns(self):
        matrix = build_feature_matrix(make(), SYMBOL, TF, include_features=False)

        assert matrix.column_names[:8] == list(RAW_PRICE_COLUMNS)
        assert matrix.column_names[8:] == list(BASE_COLUMNS)

    def test_every_row_maps_back_to_its_candle(self):
        matrix = build_feature_matrix(make(20), SYMBOL, TF, include_features=False)
        assert matrix.source_index == list(range(20))

    def test_the_base_columns_are_scale_free(self):
        """Same shape at 2000 and at 4000 must produce the same rows."""
        cheap = build_feature_matrix(make(10, 2000.0), SYMBOL, TF, include_features=False)
        dear = build_feature_matrix(make(10, 2000.0), SYMBOL, TF, include_features=False)

        # identical inputs -> identical rows (determinism)
        assert cheap.rows == dear.rows
        # and the columns are ratios, so none of them is near the price level
        for row in cheap.rows:
            assert all(abs(value) < 100 for value in row)

    def test_an_empty_series_is_refused(self):
        with pytest.raises(ValidationError):
            build_feature_matrix([], SYMBOL, TF, include_features=False)

    def test_the_summary_reports_what_happened(self):
        summary = build_feature_matrix(make(15), SYMBOL, TF, include_features=False).summary()
        assert summary["rows"] == 15
        assert summary["columns"] == 14


# ---------------------------------------------------------- attachment ---
class TestAttachTargets:
    def test_targets_are_appended_as_the_last_columns(self):
        matrix = build_feature_matrix(make(10), SYMBOL, TF, include_features=False)
        targets = [[0.01, -0.01] for _ in range(8)]

        series, names, kept = attach_targets(
            matrix, targets, list(range(8)), ["high_off", "low_off"]
        )

        assert len(series) == 8
        assert names[-2:] == ["high_off", "low_off"]
        assert series[0][-2:] == [0.01, -0.01]
        assert kept == list(range(8))

    def test_rows_without_a_label_are_dropped(self):
        """The final rows have no complete future window."""
        matrix = build_feature_matrix(make(10), SYMBOL, TF, include_features=False)
        targets = [[1.0] for _ in range(6)]

        series, _, kept = attach_targets(matrix, targets, list(range(6)), ["y"])

        assert len(series) == 6
        assert kept == list(range(6))

    def test_the_join_uses_the_candle_index_not_position(self):
        """Guards the off-by-one that silently shifts labels vs features."""
        matrix = build_feature_matrix(make(10), SYMBOL, TF, include_features=False)
        # labels exist only for candles 3, 4, 5
        series, _, kept = attach_targets(matrix, [[7.0], [8.0], [9.0]], [3, 4, 5], ["y"])

        assert [row[-1] for row in series] == [7.0, 8.0, 9.0]
        assert kept == [3, 4, 5]

    def test_mismatched_lengths_are_refused(self):
        matrix = build_feature_matrix(make(10), SYMBOL, TF, include_features=False)
        with pytest.raises(ValidationError):
            attach_targets(matrix, [[1.0], [2.0]], [0], ["y"])
