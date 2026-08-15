"""Application service: ingest market data through the Data Platform."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ShadBotTrader.core.events.event import Event
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.dataset.data_layer import DataLayer
from ShadBotTrader.domain.dataset.data_schema import candle_schema_v1
from ShadBotTrader.domain.dataset.dataset_descriptor import (
    DatasetDescriptor,
    DatasetStatus,
)
from ShadBotTrader.domain.dataset.dataset_identity import DataKind, DatasetId
from ShadBotTrader.domain.dataset.dataset_version import DatasetVersion
from ShadBotTrader.domain.dataset.events import (
    DATASET_INGESTED,
    DATASET_QUARANTINED,
    MARKET_DATA_RECEIVED,
)
from ShadBotTrader.domain.dataset.pipeline import (
    CandleNormalizerPort,
    CandleValidatorPort,
    QualityAnalyzerPort,
)
from ShadBotTrader.domain.dataset.ports import (
    CandleRepository,
    DatasetRepository,
    MarketDataProvider,
)
from ShadBotTrader.domain.dataset.quality_report import QualityIssue, QualityReport
from ShadBotTrader.domain.market.timeframe import Timeframe


@dataclass(frozen=True)
class IngestionResult:
    """The outcome of a single ingestion run."""

    symbol: str
    timeframe: str
    version: int
    raw_row_count: int
    candle_count: int
    quality_report: QualityReport
    validation_issues: List[QualityIssue] = field(default_factory=list)
    descriptors: List[DatasetDescriptor] = field(default_factory=list)

    @property
    def quarantined(self) -> bool:
        """True when the dataset was flagged as critically invalid."""
        return self.quality_report.has_critical


class DataIngestionService:
    """Orchestrates the L0 → L1 → L2 → L3 ingestion pipeline.

    Flow (matching Phase 11):

    1. fetch raw records from the provider (L0/L1)
    2. validate them (L2)
    3. normalise the valid ones into domain candles (L3)
    4. run the quality engine
    5. persist raw + normalized data immutably (Parquet)
    6. register both datasets in the catalog
    7. publish ``MarketDataReceived`` and ``DatasetIngested`` events
    """

    def __init__(
        self,
        provider: MarketDataProvider,
        validator: CandleValidatorPort,
        normalizer: CandleNormalizerPort,
        quality_analyzer: QualityAnalyzerPort,
        candle_repository: CandleRepository,
        dataset_repository: DatasetRepository,
        event_bus: EventBus,
    ) -> None:
        self._provider = provider
        self._validator = validator
        self._normalizer = normalizer
        self._quality_analyzer = quality_analyzer
        self._candle_repository = candle_repository
        self._dataset_repository = dataset_repository
        self._event_bus = event_bus

    def ingest(self, symbol: str, timeframe: str, source: str) -> IngestionResult:
        """Run the full ingestion pipeline for one symbol/timeframe."""
        timeframe_vo = Timeframe(timeframe)

        raw_records = self._provider.fetch_candles(symbol, timeframe, source)
        self._event_bus.publish(
            Event(
                event_type=MARKET_DATA_RECEIVED,
                source=self._provider.provider_name,
                payload={"symbol": symbol, "timeframe": timeframe, "count": len(raw_records)},
            )
        )

        validation = self._validator.validate(raw_records)
        normalization = self._normalizer.normalize(validation.records)
        quality = self._quality_analyzer.analyze(normalization.candles, timeframe_vo)

        raw_id = DatasetId(
            provider=self._provider.provider_name,
            kind=DataKind.MARKET_CANDLE,
            symbol=symbol,
            timeframe=timeframe,
            layer=DataLayer.RAW.value,
        )
        normalized_id = DatasetId(
            provider=self._provider.provider_name,
            kind=DataKind.MARKET_CANDLE,
            symbol=symbol,
            timeframe=timeframe,
            layer=DataLayer.NORMALIZED.value,
        )

        # The persisted store is the source of truth for versions across
        # runs; the in-memory catalog only tracks the current session. Take
        # the maximum so a re-run never tries to overwrite an immutable
        # version (raw immutability).
        version = max(
            self._dataset_repository.next_version(raw_id),
            self._candle_repository.next_version(raw_id),
        )
        schema = candle_schema_v1()

        if raw_records:
            self._candle_repository.save_raw(raw_id, version, raw_records)
        if normalization.candles:
            self._candle_repository.save_normalized(normalized_id, version, normalization.candles)

        time_start = normalization.candles[0].open_time.value if normalization.candles else None
        time_end = normalization.candles[-1].open_time.value if normalization.candles else None
        status = DatasetStatus.QUARANTINED if quality.has_critical else DatasetStatus.ACTIVE

        raw_descriptor = DatasetDescriptor(
            dataset_id=raw_id,
            version=DatasetVersion(version),
            schema=schema,
            layer=DataLayer.RAW,
            status=status,
            row_count=len(raw_records),
            quality=quality,
        )
        normalized_descriptor = DatasetDescriptor(
            dataset_id=normalized_id,
            version=DatasetVersion(version),
            schema=schema,
            layer=DataLayer.NORMALIZED,
            status=status,
            time_start=time_start,
            time_end=time_end,
            row_count=len(normalization.candles),
            quality=quality,
        )

        self._dataset_repository.register(raw_descriptor)
        self._dataset_repository.register(normalized_descriptor)

        event_type = DATASET_QUARANTINED if quality.has_critical else DATASET_INGESTED
        self._event_bus.publish(
            Event(
                event_type=event_type,
                source="DataIngestionService",
                payload={
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "version": version,
                    "candle_count": len(normalization.candles),
                    "quality_score": float(quality.score.overall),
                },
            )
        )

        return IngestionResult(
            symbol=symbol,
            timeframe=timeframe,
            version=version,
            raw_row_count=len(raw_records),
            candle_count=len(normalization.candles),
            quality_report=quality,
            validation_issues=list(validation.issues) + list(normalization.issues),
            descriptors=[raw_descriptor, normalized_descriptor],
        )
