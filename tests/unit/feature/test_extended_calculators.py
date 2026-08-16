"""Tests for balance, pca and divergence calculators."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition, FeatureId
from ShadBotTrader.domain.feature.feature_types import (
    Causality,
    FeatureType,
    FeatureValueType,
)
from ShadBotTrader.domain.feature.ports import FeatureInputContext
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.feature.calculators.balance import BalanceCalculator
from ShadBotTrader.infrastructure.feature.calculators.divergence import (
    DivergenceCalculator,
)
from ShadBotTrader.infrastructure.feature.calculators.pca import PcaCalculator


def _definition(
    feature_id: str, parameters: dict, family: str, causality: Causality = Causality.CAUSAL
) -> FeatureDefinition:
    return FeatureDefinition(
        feature_id=FeatureId(feature_id),
        name=feature_id,
        feature_type=FeatureType.DERIVED,
        value_type=FeatureValueType.SCALAR,
        parameters=parameters,
        lookback=0,
        computation_version="1",
        family=family,
        causality=causality,
    )


def _context(closes: list[float], opens: list[float] | None = None) -> FeatureInputContext:
    start = datetime(2024, 1, 2, 8, 0, tzinfo=timezone.utc)
    opens = opens if opens is not None else [c - 0.5 for c in closes]
    candles = []
    for index, close in enumerate(closes):
        open_price = opens[index]
        candles.append(
            Candle(
                symbol=Symbol("XAUUSD_i"),
                timeframe=Timeframe("5M"),
                open_time=Timestamp(start + index * timedelta(minutes=5)),
                open_price=Price(str(100 + open_price)),
                high=Price(str(100 + max(open_price, close) + 1)),
                low=Price(str(100 + min(open_price, close) - 1)),
                close=Price(str(100 + close)),
                volume=Decimal(str(100 + index)),
            )
        )
    return FeatureInputContext(Symbol("XAUUSD_i"), Timeframe("5M"), candles)


def test_color_candle_is_binary():
    context = _context([1.0, 0.5, 2.0, 1.5], opens=[0.5, 1.0, 1.0, 2.0])
    result = BalanceCalculator().compute(
        _definition("color_candle", {"kind": "color"}, "balance"), context
    )
    values = [p.value for p in result.points]
    assert all(value in (0.0, 1.0) for value in values)


def test_power_green_zero_on_red_candles():
    context = _context([1.0, -1.0, 1.0, -1.0], opens=[0.0, 0.0, 0.0, 0.0])
    result = BalanceCalculator().compute(
        _definition("power_green", {"kind": "power", "color": "green"}, "balance"),
        context,
    )
    # red candles (close < open) must be zero
    assert result.points[1].value == 0.0
    assert result.points[0].value > 0.0  # green candle has positive power


def test_pca_component_shape():
    context = _context([float(i) for i in range(1, 40)])
    result = PcaCalculator().compute(
        _definition("pca0", {"component": 0}, "pca", Causality.NON_CAUSAL), context
    )
    assert len(result.points) == 39
    assert all(p.value is not None for p in result.points)


def test_pca_components_differ():
    context = _context([float(i) for i in range(1, 40)])
    first = PcaCalculator().compute(
        _definition("pca0", {"component": 0}, "pca", Causality.NON_CAUSAL), context
    )
    second = PcaCalculator().compute(
        _definition("pca1", {"component": 1}, "pca", Causality.NON_CAUSAL), context
    )
    v0 = [p.value for p in first.points]
    v1 = [p.value for p in second.points]
    assert v0 != v1


def test_divergence_is_binary_and_bounded():
    # a series with a clear lower-low structure for the oscillator to diverge
    closes = [10, 9, 8, 9, 7.5, 8, 7, 8, 6.5, 7, 6, 7, 5.5, 6, 5, 6]
    context = _context(closes)
    result = DivergenceCalculator().compute(
        _definition(
            "rsi_buy_primary",
            {"indicator": "rsi", "signaltype": "buy"},
            "divergence",
        ),
        context,
    )
    values = [p.value for p in result.points]
    assert all(value in (0.0, 1.0) for value in values)


def test_divergence_sell_runs():
    context = _context([float(i % 7) for i in range(60)])
    result = DivergenceCalculator().compute(
        _definition(
            "rsi_sell_primary",
            {"indicator": "rsi", "signaltype": "sell"},
            "divergence",
        ),
        context,
    )
    assert len(result.points) == 60
    assert all(p.value in (0.0, 1.0) for p in result.points)
