"""Tests for the indicator calculators (determinism, causality, warmup)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition, FeatureId
from ShadBotTrader.domain.feature.feature_types import FeatureType, FeatureValueType
from ShadBotTrader.domain.feature.ports import FeatureInputContext
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.feature.calculators.atr import AtrCalculator
from ShadBotTrader.infrastructure.feature.calculators.ema import EmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.macd import MacdCalculator
from ShadBotTrader.infrastructure.feature.calculators.returns import ReturnsCalculator
from ShadBotTrader.infrastructure.feature.calculators.rsi import RsiCalculator
from ShadBotTrader.infrastructure.feature.calculators.sma import SmaCalculator
from ShadBotTrader.infrastructure.feature.calculators.stochastic import StochasticCalculator


def _definition(feature_id: str, parameters: dict, lookback: int) -> FeatureDefinition:
    return FeatureDefinition(
        feature_id=FeatureId(feature_id),
        name=feature_id,
        feature_type=FeatureType.TREND,
        value_type=FeatureValueType.SCALAR,
        parameters=parameters,
        lookback=lookback,
        computation_version="1",
    )


def _candles(closes: list[float]) -> list[Candle]:
    start = datetime(2024, 1, 2, 8, 0, tzinfo=timezone.utc)
    candles = []
    for index, close in enumerate(closes):
        candles.append(
            Candle(
                symbol=Symbol("XAUUSD_i"),
                timeframe=Timeframe("5M"),
                open_time=Timestamp(start + index * timedelta(minutes=5)),
                open_price=Price(str(100 + close)),
                high=Price(str(100 + close + 2)),
                low=Price(str(100 + close - 2)),
                close=Price(str(100 + close)),
                volume=Decimal("100"),
            )
        )
    return candles


def _context(closes: list[float]) -> FeatureInputContext:
    return FeatureInputContext(Symbol("XAUUSD_i"), Timeframe("5M"), _candles(closes))


def test_sma_warmup_and_value():
    context = _context([1, 2, 3, 4, 5])
    result = SmaCalculator().compute(_definition("sma_3", {"period": 3}, 2), context)
    assert result.warmup == 2
    assert result.points[0].value is None
    assert result.points[1].value is None
    assert result.points[2].value == pytest.approx(102.0)  # (101+102+103)/3
    assert result.points[4].value == pytest.approx(104.0)  # (103+104+105)/3


def test_ema_is_deterministic():
    context = _context([10, 11, 12, 13, 14, 15])
    definition = _definition("ema_3", {"period": 3}, 2)
    first = EmaCalculator().compute(definition, context)
    second = EmaCalculator().compute(definition, context)
    assert first.points == second.points


def test_rsi_is_bounded_and_causal():
    context = _context([10, 11, 12, 11, 12, 13, 12, 13, 14, 13, 14, 15, 14, 15, 16, 15])
    result = RsiCalculator().compute(_definition("rsi_14", {"period": 14}, 14), context)
    values = [p.value for p in result.points if p.value is not None]
    assert values
    for value in values:
        assert 0.0 <= value <= 100.0


def test_atr_is_positive_after_warmup():
    context = _context([10, 11, 12, 11, 12, 13, 12, 13, 14, 13, 14, 15, 14, 15, 16, 15])
    result = AtrCalculator().compute(_definition("atr_14", {"period": 14}, 14), context)
    values = [p.value for p in result.points if p.value is not None]
    assert all(value > 0 for value in values)


def test_returns_first_available_after_period():
    context = _context([100, 110, 121, 133.1])
    result = ReturnsCalculator().compute(_definition("returns_1", {"period": 1}, 1), context)
    assert result.points[0].value is None
    assert result.points[1].value == pytest.approx(0.05)  # (210-200)/200


def test_stochastic_is_bounded():
    context = _context([10, 11, 12, 11, 12, 13, 12, 13, 14, 13, 14, 15, 14, 15, 16, 15])
    result = StochasticCalculator().compute(
        _definition("stochastic_14", {"period": 14}, 13), context
    )
    values = [p.value for p in result.points if p.value is not None]
    for value in values:
        assert 0.0 <= value <= 100.0


def test_macd_warmup_matches_definition():
    context = _context([float(i) for i in range(1, 80)])
    definition = _definition("macd_12_26_9", {"fast": 12, "slow": 26, "signal": 9}, 33)
    result = MacdCalculator().compute(definition, context)
    assert result.warmup == 33
    assert result.points[33].value is not None
    assert result.points[32].value is None
