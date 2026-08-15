"""Tests for the CandleNormalizer (L3)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.domain.dataset.pipeline import ValidatedCandleRecord
from ShadBotTrader.infrastructure.data.candle_normalizer import CandleNormalizer


def _record(symbol: str = "XAUUSD_i", timeframe: str = "5M", tz=None) -> ValidatedCandleRecord:
    tz = tz or timezone.utc
    return ValidatedCandleRecord(
        symbol=symbol,
        timeframe=timeframe,
        open_time=datetime(2024, 1, 2, 8, 0, tzinfo=tz),
        open=Decimal("2000.00"),
        high=Decimal("2005.00"),
        low=Decimal("1995.00"),
        close=Decimal("2002.00"),
        volume=Decimal("100"),
    )


def test_normalizes_into_domain_candle():
    result = CandleNormalizer().normalize([_record()])
    assert len(result.candles) == 1
    candle = result.candles[0]
    assert str(candle.symbol) == "XAUUSD_I"
    assert candle.close.amount == Decimal("2002.00")


def test_symbol_separators_removed():
    result = CandleNormalizer().normalize([_record(symbol="EUR/USD")])
    assert str(result.candles[0].symbol) == "EURUSD"


def test_symbol_lowercase_uppercased():
    result = CandleNormalizer().normalize([_record(symbol="xauusd_i")])
    assert str(result.candles[0].symbol) == "XAUUSD_I"


def test_non_utc_timestamp_converted_to_utc():
    result = CandleNormalizer().normalize([_record(tz=timezone(timedelta(hours=2)))])
    candle = result.candles[0]
    assert candle.open_time.value.utcoffset().total_seconds() == 0


def test_invalid_timeframe_is_flagged_not_crashed():
    result = CandleNormalizer().normalize([_record(timeframe="5X")])
    assert result.candles == []
    assert result.issues[0].code == "NORMALIZATION_FAILED"
