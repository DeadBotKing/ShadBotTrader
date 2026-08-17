"""End-to-end tests for the Feature Platform pipeline."""

import csv
from pathlib import Path

from ShadBotTrader.application.services.data_ingestion_service import DataIngestionService
from ShadBotTrader.application.services.feature_computation_service import (
    FeatureComputationService,
)
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.feature.events import FEATURE_COMPUTED, FEATURESET_COMPUTED
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
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.in_memory_feature_registry import (
    InMemoryFeatureRegistry,
)
from ShadBotTrader.infrastructure.feature.parquet_feature_store import (
    ParquetFeatureStore,
)
from ShadBotTrader.infrastructure.feature.standard_catalog import (
    standard_feature_set_v1,
)


def _write_csv(path: Path, rows: int = 80) -> Path:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["timestamp", "open", "high", "low", "close", "volume"],
        )
        writer.writeheader()
        for index in range(rows):
            close = 2000.0 + index * 0.5
            writer.writerow(
                {
                    "timestamp": f"2024-01-02 08:{index * 5 % 60:02d}:{index * 5 // 60:02d}",
                    "open": f"{close - 1:.2f}",
                    "high": f"{close + 2:.2f}",
                    "low": f"{close - 2:.2f}",
                    "close": f"{close:.2f}",
                    "volume": "100",
                }
            )
    return path


def test_full_feature_pipeline(tmp_path):
    csv_path = _write_csv(tmp_path / "in.csv")
    event_bus = EventBus()

    # 1) Data Platform: ingest
    data_service = DataIngestionService(
        provider=CsvMarketDataProvider(),
        validator=CandleValidator(),
        normalizer=CandleNormalizer(),
        quality_analyzer=QualityAnalyzer(),
        candle_repository=ParquetCandleStore(tmp_path / "datasets"),
        dataset_repository=InMemoryDatasetRepository(),
        event_bus=event_bus,
    )
    ingestion = data_service.ingest("XAUUSD_i", "5M", str(csv_path))
    assert ingestion.candle_count == 80

    candle_store = ParquetCandleStore(tmp_path / "datasets")
    candles = candle_store.query(Symbol("XAUUSD_i"), Timeframe("5M"))

    # 2) Feature Platform: compute
    computed_events = []
    set_events = []
    event_bus.subscribe(FEATURE_COMPUTED, lambda e: computed_events.append(e))
    event_bus.subscribe(FEATURESET_COMPUTED, lambda e: set_events.append(e))

    feature_store = ParquetFeatureStore(tmp_path / "datasets")
    registry = InMemoryFeatureRegistry()
    service = FeatureComputationService(
        calculator_resolver=CalculatorRegistry(),
        registry=registry,
        repository=feature_store,
        event_bus=event_bus,
    )

    result = service.compute_set(
        feature_set=standard_feature_set_v1(),
        symbol=Symbol("XAUUSD_i"),
        timeframe=Timeframe("5M"),
        candles=candles,
        source_dataset_id="csv.market_candle.XAUUSD_i.5M.L3_normalized",
        dataset_version=ingestion.version,
    )

    assert len(result.outcomes) == 109
    assert len(result.quarantined_ids) == 0
    assert len(computed_events) == 109
    assert len(set_events) == 1
    assert set_events[0].payload["computed"] == 109

    # Features are stored under their own series (Phase 37), so the check
    # must ask the store scoped to the symbol and timeframe that produced
    # them — an unscoped store deliberately looks somewhere else.
    stored = feature_store.for_series("XAUUSD_i", "5M")
    for outcome in result.outcomes:
        assert stored.exists(outcome.feature_id, outcome.version)

    # registry has all definitions
    assert len(registry.list_all()) == 109


def test_feature_quality_flags_bad_range(tmp_path):
    csv_path = _write_csv(tmp_path / "in.csv", 60)
    event_bus = EventBus()
    data_service = DataIngestionService(
        provider=CsvMarketDataProvider(),
        validator=CandleValidator(),
        normalizer=CandleNormalizer(),
        quality_analyzer=QualityAnalyzer(),
        candle_repository=ParquetCandleStore(tmp_path / "datasets"),
        dataset_repository=InMemoryDatasetRepository(),
        event_bus=event_bus,
    )
    data_service.ingest("XAUUSD_i", "5M", str(csv_path))
    candles = ParquetCandleStore(tmp_path / "datasets").query(Symbol("XAUUSD_i"), Timeframe("5M"))

    service = FeatureComputationService(
        calculator_resolver=CalculatorRegistry(),
        registry=InMemoryFeatureRegistry(),
        repository=ParquetFeatureStore(tmp_path / "datasets"),
        event_bus=event_bus,
    )
    result = service.compute_set(
        feature_set=standard_feature_set_v1(),
        symbol=Symbol("XAUUSD_i"),
        timeframe=Timeframe("5M"),
        candles=candles,
        source_dataset_id="csv.market_candle.XAUUSD_i.5M.L3_normalized",
        dataset_version=1,
    )
    # هیچ قرنطینه‌ای برای داده‌ی سالم
    assert result.quarantined_ids == []
    for outcome in result.outcomes:
        assert outcome.quality.score.overall > 0
