"""Tests for the ParquetCandleStore (L1 raw immutability + L3 query)."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from ShadBotTrader.domain.dataset.data_layer import DataLayer
from ShadBotTrader.domain.dataset.dataset_identity import DataKind, DatasetId
from ShadBotTrader.domain.dataset.raw_record import RawCandleRecord
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore


def _raw_id() -> DatasetId:
    return DatasetId("csv", DataKind.MARKET_CANDLE, "XAUUSD_i", "5M", DataLayer.RAW.value)


def _normalized_id() -> DatasetId:
    return DatasetId("csv", DataKind.MARKET_CANDLE, "XAUUSD_i", "5M", DataLayer.NORMALIZED.value)


def _record(timestamp: str) -> RawCandleRecord:
    return RawCandleRecord.from_mapping(
        {
            "timestamp": timestamp,
            "open": "2000.00",
            "high": "2005.00",
            "low": "1995.00",
            "close": "2002.00",
            "volume": "100",
        },
        default_symbol="XAUUSD_i",
        default_timeframe="5M",
    )


def _candle(minute: int) -> Candle:
    open_time = datetime(2024, 1, 2, 8, minute, tzinfo=timezone.utc)
    return Candle(
        symbol=Symbol("XAUUSD_i"),
        timeframe=Timeframe("5M"),
        open_time=Timestamp(open_time),
        open_price=Price("2000.00"),
        high=Price("2005.00"),
        low=Price("1995.00"),
        close=Price("2002.00"),
        volume=Decimal("100"),
    )


def test_raw_immutability_refuses_overwrite(tmp_path):
    store = ParquetCandleStore(tmp_path)
    store.save_raw(_raw_id(), 1, [_record("2024-01-02 08:00:00")])
    with pytest.raises(FileExistsError):
        store.save_raw(_raw_id(), 1, [_record("2024-01-02 08:00:00")])


def test_query_returns_normalized_candles(tmp_path):
    store = ParquetCandleStore(tmp_path)
    store.save_normalized(_normalized_id(), 1, [_candle(0), _candle(5)])
    candles = store.query(Symbol("XAUUSD_i"), Timeframe("5M"))
    assert len(candles) == 2
    assert candles[0].open_time.value.minute == 0


def test_query_filters_by_time_range(tmp_path):
    store = ParquetCandleStore(tmp_path)
    store.save_normalized(_normalized_id(), 1, [_candle(0), _candle(5), _candle(10)])
    start = datetime(2024, 1, 2, 8, 5, tzinfo=timezone.utc)
    candles = store.query(Symbol("XAUUSD_i"), Timeframe("5M"), start=start)
    assert len(candles) == 2
    assert candles[0].open_time.value.minute == 5


def test_query_empty_store_returns_empty(tmp_path):
    store = ParquetCandleStore(tmp_path)
    assert store.query(Symbol("XAUUSD_i"), Timeframe("5M")) == []


def test_next_version_reflects_persisted_files(tmp_path):
    store = ParquetCandleStore(tmp_path)
    assert store.next_version(_raw_id()) == 1
    store.save_raw(_raw_id(), 1, [_record("2024-01-02 08:00:00")])
    assert store.next_version(_raw_id()) == 2
    store.save_raw(_raw_id(), 2, [_record("2024-01-02 08:05:00")])
    assert store.next_version(_raw_id()) == 3


def test_next_version_ignores_non_version_files(tmp_path):
    store = ParquetCandleStore(tmp_path)
    store.save_raw(_raw_id(), 1, [_record("2024-01-02 08:00:00")])
    # یک فایل غیر نسخه‌ای داخل همان پوشه بگذاریم
    directory = tmp_path / "raw" / "XAUUSD_I" / "5M"
    (directory / "notes.txt").write_text("hi", encoding="utf-8")
    assert store.next_version(_raw_id()) == 2
