"""Application service: compute features over Data Platform candles."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from ShadBotTrader.core.events.event import Event
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.feature.events import (
    FEATURE_COMPUTED,
    FEATURE_QUARANTINED,
    FEATURESET_COMPUTED,
)
from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_quality import FeatureQualityReport
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.feature_set import FeatureSet
from ShadBotTrader.domain.feature.ports import (
    FeatureCalculator,
    FeatureInputContext,
    FeatureRegistry,
    FeatureRepository,
)
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.feature.feature_quality_engine import FeatureQualityEngine
from ShadBotTrader.infrastructure.feature.leakage_checker import LeakageChecker
from ShadBotTrader.infrastructure.feature.standard_catalog import value_ranges


@dataclass(frozen=True)
class FeatureComputationOutcome:
    """The outcome of computing a single feature."""

    feature_id: str
    version: int
    available_count: int
    quality: FeatureQualityReport
    live_compatible: bool
    quarantined: bool


@dataclass(frozen=True)
class FeatureSetComputationResult:
    """The outcome of computing a whole feature set."""

    set_name: str
    symbol: str
    timeframe: str
    source_dataset_id: str
    dataset_version: int
    outcomes: List[FeatureComputationOutcome] = field(default_factory=list)

    @property
    def quarantined_ids(self) -> List[str]:
        return [outcome.feature_id for outcome in self.outcomes if outcome.quarantined]


class FeatureComputationService:
    """Orchestrates compute -> validate -> leakage -> store -> publish.

    Pipeline (Phase 12, section 3): data access -> computation ->
    validation -> leakage check -> version -> storage -> serving.
    Invalid features are quarantined and never stored/served.
    """

    def __init__(
        self,
        calculator_resolver,
        registry: FeatureRegistry,
        repository: FeatureRepository,
        event_bus: EventBus,
    ) -> None:
        self._resolver = calculator_resolver
        self._registry = registry
        self._repository = repository
        self._event_bus = event_bus
        self._quality_engine = FeatureQualityEngine()
        self._leakage_checker = LeakageChecker()

    def compute_feature(
        self,
        definition: FeatureDefinition,
        context: FeatureInputContext,
        source_dataset_id: str,
        dataset_version: int,
    ) -> FeatureComputationOutcome:
        """Compute, validate and store one feature."""
        calculator: Optional[FeatureCalculator] = self._resolver.resolve(
            definition.feature_id.value
        )
        if calculator is None:
            raise LookupError(f"No calculator registered for {definition.feature_id.value}")

        result: FeatureResult = calculator.compute(definition, context)

        leakage = self._leakage_checker.check(definition, result)
        quality = self._quality_engine.check(
            result, context, value_range=value_ranges(definition.feature_id.value)
        )

        # Quarantine only on fatal quality problems (empty / misaligned /
        # non-finite). Non-causal features are stored for research but
        # flagged live_incompatible (Phase 12, sections 29 + 47-48).
        if quality.is_empty or quality.has_fatal:
            self._event_bus.publish(
                Event(
                    event_type=FEATURE_QUARANTINED,
                    source="FeatureComputationService",
                    payload={
                        "feature_id": definition.feature_id.value,
                        "reason": [issue.code.value for issue in quality.issues],
                    },
                )
            )
            return FeatureComputationOutcome(
                feature_id=definition.feature_id.value,
                version=0,
                available_count=result.available_count,
                quality=quality,
                live_compatible=leakage.live_compatible,
                quarantined=True,
            )

        version = self._repository.next_version(definition.feature_id.value)
        self._repository.save(definition.feature_id.value, version, result)
        self._registry.register(definition)

        self._event_bus.publish(
            Event(
                event_type=FEATURE_COMPUTED,
                source="FeatureComputationService",
                payload={
                    "feature_id": definition.feature_id.value,
                    "version": version,
                    "available_count": result.available_count,
                    "quality_score": float(quality.score.overall),
                },
            )
        )

        return FeatureComputationOutcome(
            feature_id=definition.feature_id.value,
            version=version,
            available_count=result.available_count,
            quality=quality,
            live_compatible=leakage.live_compatible,
            quarantined=False,
        )

    def compute_set(
        self,
        feature_set: FeatureSet,
        symbol: Symbol,
        timeframe: Timeframe,
        candles: List[Candle],
        source_dataset_id: str,
        dataset_version: int,
    ) -> FeatureSetComputationResult:
        """Compute every feature of ``feature_set`` over ``candles``."""
        context = FeatureInputContext(symbol=symbol, timeframe=timeframe, candles=candles)
        outcomes: List[FeatureComputationOutcome] = []
        for definition in feature_set.definitions:
            outcomes.append(
                self.compute_feature(
                    definition=definition,
                    context=context,
                    source_dataset_id=source_dataset_id,
                    dataset_version=dataset_version,
                )
            )

        self._event_bus.publish(
            Event(
                event_type=FEATURESET_COMPUTED,
                source="FeatureComputationService",
                payload={
                    "set_name": feature_set.name,
                    "symbol": str(symbol),
                    "timeframe": str(timeframe),
                    "computed": sum(1 for outcome in outcomes if not outcome.quarantined),
                    "quarantined": sum(1 for outcome in outcomes if outcome.quarantined),
                },
            )
        )

        return FeatureSetComputationResult(
            set_name=feature_set.name,
            symbol=str(symbol),
            timeframe=str(timeframe),
            source_dataset_id=source_dataset_id,
            dataset_version=dataset_version,
            outcomes=outcomes,
        )
