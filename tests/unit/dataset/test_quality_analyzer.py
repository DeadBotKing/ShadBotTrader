"""Tests for the QualityAnalyzer."""

from datetime import datetime, timezone
from decimal import Decimal

from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.data.quality_analyzer import QualityAnalyzer

TIMEFRAME = Timeframe("5M")


def _candle(minute: int, close: str = "2000.00", volume: str = "100") -> Candle:
    open_time = datetime(2024, 1, 2, 8, minute, tzinfo=timezone.utc)
    close_price = Decimal(close)
    return Candle(
        symbol=Symbol("XAUUSD_i"),
        timeframe=TIMEFRAME,
        open_time=Timestamp(open_time),
        open_price=Price(close_price),
        high=Price(close_price + Decimal("2")),
        low=Price(close_price - Decimal("2")),
        close=Price(close_price),
        volume=Decimal(volume),
    )


def test_clean_sequence_scores_perfect():
    candles = [_candle(0), _candle(5), _candle(10), _candle(15)]
    report = QualityAnalyzer().analyze(candles, TIMEFRAME)
    assert report.score.overall == Decimal("100.00")
    assert report.issues == []


def test_gap_detected():
    candles = [_candle(0), _candle(5), _candle(15)]  # 10 missing
    report = QualityAnalyzer().analyze(candles, TIMEFRAME)
    assert any(issue.code == "GAP_DETECTED" for issue in report.issues)
    assert report.score.timeliness < Decimal(100)


def test_duplicate_timestamp_detected():
    candles = [_candle(0), _candle(0), _candle(5)]
    report = QualityAnalyzer().analyze(candles, TIMEFRAME)
    assert any(issue.code == "DUPLICATE_TIMESTAMP" for issue in report.issues)


def test_price_outlier_detected():
    candles = [_candle(0), _candle(5), _candle(10), _candle(15, close="9000.00")]
    report = QualityAnalyzer().analyze(candles, TIMEFRAME)
    assert any(issue.code == "PRICE_OUTLIER" for issue in report.issues)


def test_empty_dataset_is_critical():
    report = QualityAnalyzer().analyze([], TIMEFRAME)
    assert report.has_critical is True
    assert report.issues[0].code == "EMPTY_DATASET"
