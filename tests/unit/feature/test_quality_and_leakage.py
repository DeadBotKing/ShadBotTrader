"""Tests for the feature quality engine and leakage checker."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition, FeatureId
from ShadBotTrader.domain.feature.feature_quality import FeatureIssueCode
from ShadBotTrader.domain.feature.feature_result import FeaturePoint, FeatureResult
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
from ShadBotTrader.infrastructure.feature.feature_quality_engine import (
    FeatureQualityEngine,
)
from ShadBotTrader.infrastructure.feature.leakage_checker import LeakageChecker


def _definition(causality: Causality = Causality.CAUSAL) -> FeatureDefinition:
    return FeatureDefinition(
        feature_id=FeatureId("rsi_14"),
        name="RSI 14",
        feature_type=FeatureType.MOMENTUM,
        value_type=FeatureValueType.SCALAR,
        parameters={"period": 14},
        lookback=14,
        computation_version="1",
        causality=causality,
    )


def _context(count: int) -> FeatureInputContext:
    start = datetime(2024, 1, 2, 8, 0, tzinfo=timezone.utc)
    candles = [
        Candle(
            symbol=Symbol("XAUUSD_i"),
            timeframe=Timeframe("5M"),
            open_time=Timestamp(start + index * timedelta(minutes=5)),
            open_price=Price("100"),
            high=Price("101"),
            low=Price("99"),
            close=Price("100"),
            volume=Decimal("10"),
        )
        for index in range(count)
    ]
    return FeatureInputContext(Symbol("XAUUSD_i"), Timeframe("5M"), candles)


def _result(context: FeatureInputContext, warmup: int = 14) -> FeatureResult:
    points = [
        FeaturePoint(
            timestamp=Timestamp(candle.open_time.value),
            value=None if index < warmup else float(50 + index),
        )
        for index, candle in enumerate(context.candles)
    ]
    return FeatureResult(feature_id="rsi_14", points=points, warmup=warmup)


def test_clean_feature_scores_perfect():
    context = _context(30)
    result = _result(context)
    report = FeatureQualityEngine().check(result, context, value_range=(0.0, 100.0))
    assert report.issues == []
    assert report.score.overall > 90


def test_out_of_range_is_flagged():
    context = _context(30)
    result = _result(context)
    report = FeatureQualityEngine().check(result, context, value_range=(0.0, 10.0))
    assert any(issue.code is FeatureIssueCode.OUT_OF_RANGE for issue in report.issues)


def test_empty_result_is_fatal():
    context = _context(30)
    result = FeatureResult(feature_id="rsi_14", points=[], warmup=0)
    report = FeatureQualityEngine().check(result, context)
    assert report.is_empty is True
    assert report.has_fatal is True


def test_misaligned_timestamps_are_fatal():
    context = _context(30)
    result = _result(context)
    wrong_timestamp = Timestamp(datetime(2025, 1, 1, tzinfo=timezone.utc))
    points = list(result.points)
    points[-1] = FeaturePoint(timestamp=wrong_timestamp, value=50.0)
    misaligned = FeatureResult(feature_id="rsi_14", points=points, warmup=14)
    report = FeatureQualityEngine().check(misaligned, context)
    assert report.has_fatal is True
    assert any(issue.code is FeatureIssueCode.TIMESTAMP_MISALIGNED for issue in report.issues)


def test_non_causal_feature_is_live_incompatible():
    context = _context(30)
    result = _result(context)
    report = LeakageChecker().check(_definition(Causality.NON_CAUSAL), result)
    assert report.passed is False
    assert report.live_compatible is False


def test_causal_feature_passes_leakage():
    context = _context(30)
    result = _result(context)
    report = LeakageChecker().check(_definition(Causality.CAUSAL), result)
    assert report.passed is True
    assert report.live_compatible is True
