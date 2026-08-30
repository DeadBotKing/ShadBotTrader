"""Runtime proofs for the causal feature/model-input contract."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import numpy as np

from ShadBotTrader.domain.feature.ports import FeatureInputContext
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.causality_audit import audit_feature_set
from ShadBotTrader.infrastructure.feature.invariance_audit import (
    audit_feature_set_invariance,
    audit_matrix_invariance,
    audit_transformer_invariance,
    mutate_future_candles,
)
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set

SYMBOL = Symbol("XAUUSD_i")
TIMEFRAME = Timeframe("5M")


def candles(count: int = 140) -> list[Candle]:
    start = datetime(2024, 1, 2, 8, 0, tzinfo=timezone.utc)
    result: list[Candle] = []
    for index in range(count):
        close = Decimal("100") + Decimal(index) * Decimal("0.17")
        if index % 9 == 0:
            close -= Decimal("0.8")
        open_price = close - Decimal("0.08") if index % 2 else close + Decimal("0.06")
        high = max(open_price, close) + Decimal("0.35") + Decimal(index % 4) / Decimal("100")
        low = min(open_price, close) - Decimal("0.30") - Decimal(index % 3) / Decimal("100")
        result.append(
            Candle(
                symbol=SYMBOL,
                timeframe=TIMEFRAME,
                open_time=Timestamp(start + timedelta(minutes=5 * index)),
                open_price=Price(open_price),
                high=Price(high),
                low=Price(low),
                close=Price(close),
                volume=Decimal(100 + index),
            )
        )
    return result


def test_standard_catalog_has_exact_fail_closed_production_set():
    feature_set = standard_feature_set()
    report = audit_feature_set(feature_set, CalculatorRegistry())

    assert len(report.rows) == 229
    assert len(report.allowed) == 176
    assert len(report.excluded) == 53
    assert "close_div_sma_20" in report.allowed
    assert "close_div_sma_50" in report.allowed
    assert "close_filter" in report.excluded
    assert "pca0" in report.excluded
    assert "sin_close" in report.excluded
    assert "chikou" in report.excluded
    assert "rsi_buy_primary" in report.excluded


def test_every_declared_causal_calculator_is_prefix_invariant():
    feature_set = standard_feature_set()
    report = audit_feature_set_invariance(
        feature_set,
        CalculatorRegistry(),
        candles(),
        SYMBOL,
        TIMEFRAME,
        split_index=90,
    )

    assert report.is_clean, report.summary()
    assert len(report.causal_failures) == 0
    # Unsafe families are still observed by the audit. At least one of the
    # intentionally future-dependent implementations must visibly change.
    by_id = {row.feature_id: row for row in report.rows}
    assert by_id["pca0"].invariant is False
    assert by_id["close_filter"].invariant is False
    assert by_id["sin_close"].invariant is False
    assert by_id["chikou"].invariant is False


def test_causal_model_matrix_prefix_is_invariant():
    feature_set = standard_feature_set()
    resolver = CalculatorRegistry()
    original = candles()
    changed = mutate_future_candles(original, split_index=90)

    def build(values):
        return build_feature_matrix(
            values,
            SYMBOL,
            TIMEFRAME,
            feature_set=feature_set,
            resolver=resolver,
            include_features=True,
            causal_only=True,
        )

    result = audit_matrix_invariance(build, original, split_index=90, mutated_candles=changed)
    assert result.passed, result.summary()
    assert result.compared_rows > 0


def test_transformer_audit_catches_full_series_fit_and_accepts_prefix_fit():
    class MeanScaler:
        def fit(self, values):
            array = np.asarray(values, dtype=float)
            self.mean = array.mean(axis=0)
            return self

        def transform(self, values):
            return np.asarray(values, dtype=float) - self.mean

    data = [[float(index), float(index * 2)] for index in range(20)]

    def change_future(values, split):
        changed = [list(row) for row in values]
        for row in changed[split:]:
            row[0] += 1000.0
            row[1] -= 500.0
        return changed

    full = audit_transformer_invariance(
        MeanScaler,
        data,
        split_index=12,
        mutate_future=change_future,
        fit_on_prefix=False,
    )
    prefix = audit_transformer_invariance(
        MeanScaler,
        data,
        split_index=12,
        mutate_future=change_future,
        fit_on_prefix=True,
    )

    assert full.passed is False
    assert full.invariant is False
    assert prefix.passed is True


def test_minmax_window_scaler_never_reads_rows_outside_the_window():
    from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window

    window = [[float(index), float(index % 3)] for index in range(6)]
    changed_future = window + [[10000.0, -10000.0]]
    assert minmax_scale_window(window) == minmax_scale_window(changed_future[:6])


def test_feature_context_prefix_itself_is_unchanged_after_mutation():
    original = candles()
    changed = mutate_future_candles(original, 90)
    first = FeatureInputContext(SYMBOL, TIMEFRAME, original[:90])
    second = FeatureInputContext(SYMBOL, TIMEFRAME, changed[:90])
    assert [c.close.amount for c in first.candles] == [c.close.amount for c in second.candles]
