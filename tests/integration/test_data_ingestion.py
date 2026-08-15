"""End-to-end tests for the Data Platform ingestion pipeline."""

import csv
from pathlib import Path

from ShadBotTrader.application.services.data_ingestion_service import DataIngestionService
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.dataset.events import DATASET_INGESTED, MARKET_DATA_RECEIVED
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.data.candle_normalizer import CandleNormalizer
from ShadBotTrader.infrastructure.data.candle_validator import CandleValidator
from ShadBotTrader.infrastructure.data.csv_market_data_provider import CsvMarketDataProvider
from ShadBotTrader.infrastructure.data.in_memory_dataset_catalog import (
    InMemoryDatasetRepository,
)
from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore
from ShadBotTrader.infrastructure.data.quality_analyzer import QualityAnalyzer


def _write_csv(path: Path, rows: list[dict]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


def _build_service(tmp_path: Path):
    event_bus = EventBus()
    received: list = []
    ingested: list = []
    event_bus.subscribe(MARKET_DATA_RECEIVED, lambda e: received.append(e))
    event_bus.subscribe(DATASET_INGESTED, lambda e: ingested.append(e))

    store = ParquetCandleStore(tmp_path / "datasets")
    catalog = InMemoryDatasetRepository()
    service = DataIngestionService(
        provider=CsvMarketDataProvider(),
        validator=CandleValidator(),
        normalizer=CandleNormalizer(),
        quality_analyzer=QualityAnalyzer(),
        candle_repository=store,
        dataset_repository=catalog,
        event_bus=event_bus,
    )
    return service, store, catalog, received, ingested


def _good_rows(count: int = 5) -> list[dict]:
    rows = []
    for i in range(count):
        rows.append(
            {
                "timestamp": f"2024-01-02 08:{i * 5:02d}:00",
                "open": "2000.00",
                "high": "2005.00",
                "low": "1995.00",
                "close": "2002.00",
                "volume": "100",
            }
        )
    return rows


def test_full_pipeline_ingest_catalog_and_query(tmp_path):
    csv_path = _write_csv(tmp_path / "in.csv", _good_rows())
    service, store, catalog, received, ingested = _build_service(tmp_path)

    result = service.ingest("XAUUSD_i", "5M", str(csv_path))

    assert result.candle_count == 5
    assert result.version == 1
    assert result.quarantined is False

    # events published
    assert len(received) == 1
    assert len(ingested) == 1
    assert ingested[0].payload["candle_count"] == 5

    # catalog has both raw + normalized entries
    assert len(catalog.list_all()) == 2

    # parquet files written for raw (L1) and normalized (L3)
    assert list((tmp_path / "datasets" / "raw").rglob("*.parquet"))
    assert list((tmp_path / "datasets" / "processed").rglob("*.parquet"))

    # query returns normalized candles
    candles = store.query(Symbol("XAUUSD_i"), Timeframe("5M"))
    assert len(candles) == 5
    assert str(candles[0].symbol) == "XAUUSD_I"


def test_second_ingestion_bumps_version(tmp_path):
    csv_path = _write_csv(tmp_path / "in.csv", _good_rows())
    service, store, catalog, _, _ = _build_service(tmp_path)

    first = service.ingest("XAUUSD_i", "5M", str(csv_path))
    second = service.ingest("XAUUSD_i", "5M", str(csv_path))

    assert first.version == 1
    assert second.version == 2
    assert len(catalog.list_all()) == 4  # two datasets x two versions


def test_invalid_rows_are_flagged_and_quarantined(tmp_path):
    rows = _good_rows(3)
    rows.append(
        {
            "timestamp": "2024-01-02 08:15:00",
            "open": "2000.00",
            "high": "1990.00",  # high < low -> invalid
            "low": "1995.00",
            "close": "2002.00",
            "volume": "100",
        }
    )
    csv_path = _write_csv(tmp_path / "in.csv", rows)
    service, store, catalog, _, ingested = _build_service(tmp_path)

    result = service.ingest("XAUUSD_i", "5M", str(csv_path))

    assert result.raw_row_count == 4
    assert result.candle_count == 3  # the bad row was rejected
    assert any(issue.code == "HIGH_LOW_VIOLATION" for issue in result.validation_issues)
    # normalized descriptor exists with the valid subset
    candles = store.query(Symbol("XAUUSD_i"), Timeframe("5M"))
    assert len(candles) == 3
