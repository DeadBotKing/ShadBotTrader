"""Tests for the CandleValidator (L2)."""

from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord
from ShadBotTrader.infrastructure.data.candle_validator import CandleValidator


def _record(**overrides) -> RawCandleRecord:
    base = {
        "timestamp": "2024-01-02 08:00:00",
        "open": "2000.00",
        "high": "2005.00",
        "low": "1995.00",
        "close": "2002.00",
        "volume": "100",
    }
    base.update(overrides)
    return RawCandleRecord.from_mapping(base, default_symbol="XAUUSD_i", default_timeframe="5M")


def test_valid_records_pass():
    records = [_record(), _record(timestamp="2024-01-02 08:05:00")]
    result = CandleValidator().validate(records)
    assert result.records.__len__() == 2
    assert result.issues == []


def test_missing_required_field_is_critical():
    result = CandleValidator().validate([_record(volume="")])
    assert len(result.records) == 0
    assert result.issues[0].code == "MISSING_REQUIRED_FIELDS"


def test_high_below_low_is_critical():
    result = CandleValidator().validate([_record(high="1990.00", low="1995.00")])
    assert result.issues[0].code == "HIGH_LOW_VIOLATION"


def test_non_positive_price_is_critical():
    result = CandleValidator().validate([_record(close="0")])
    assert result.issues[0].code == "INVALID_PRICE"


def test_invalid_timestamp_is_critical():
    result = CandleValidator().validate([_record(timestamp="not-a-time")])
    assert result.issues[0].code == "INVALID_TIMESTAMP"


def test_naive_timestamp_is_made_aware():
    result = CandleValidator().validate([_record()])
    open_time = result.records[0].open_time
    assert open_time.tzinfo is not None
