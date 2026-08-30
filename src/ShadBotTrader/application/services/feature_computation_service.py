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
from ShadBotTrader.infrastructure.feature.feature_cache import (
    FeatureCache,
    FeatureFingerprint,
)
from ShadBotTrader.infrastructure.feature.feature_progress import (
    FeatureProgressReporter,
    NullFeatureProgress,
)
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
    #: True when this came from the store instead of being recomputed.
    from_cache: bool = False


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

    @property
    def reused_count(self) -> int:
        """How many features were served from the store (Phase 38)."""
        return sum(1 for outcome in self.outcomes if outcome.from_cache)

    @property
    def from_cache(self) -> bool:
        """True when nothing had to be recomputed."""
        return bool(self.outcomes) and all(outcome.from_cache for outcome in self.outcomes)


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
        progress: Optional["FeatureProgressReporter"] = None,
    ) -> None:
        self._resolver = calculator_resolver
        self._registry = registry
        self._repository = repository
        self._event_bus = event_bus
        self._quality_engine = FeatureQualityEngine()
        self._leakage_checker = LeakageChecker()
        # Phase 37: the catalogue over 100k candles takes minutes and used
        # to print nothing at all, so a slow calculator was
        # indistinguishable from a hang.
        self._progress: FeatureProgressReporter = progress or NullFeatureProgress()

    def compute_feature(
        self,
        definition: FeatureDefinition,
        context: FeatureInputContext,
        source_dataset_id: str,
        dataset_version: int,
    ) -> FeatureComputationOutcome:
        """Compute, validate and store one feature."""
        calculator: Optional[FeatureCalculator] = self._resolver.resolve(
            definition.calculator_family
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

    def _result_from_cache(
        self,
        feature_set: FeatureSet,
        symbol: Symbol,
        timeframe: Timeframe,
        source_dataset_id: str,
        dataset_version: int,
        cached: dict,
    ) -> FeatureSetComputationResult:
        """Describe a cache hit in the same shape as a real computation.

        The caller must not be able to tell the difference, except that
        it was instant. ``version`` reports the stored version actually
        reused, so the result still says which bytes were served.
        """
        outcomes: List[FeatureComputationOutcome] = []
        for definition in feature_set.definitions:
            feature_id = definition.feature_id.value
            result = cached[feature_id]
            leakage = self._leakage_checker.check(definition, result)
            outcomes.append(
                FeatureComputationOutcome(
                    feature_id=feature_id,
                    version=self._repository.next_version(feature_id) - 1,
                    available_count=result.available_count,
                    quality=self._quality_engine.check(
                        result,
                        FeatureInputContext(symbol=symbol, timeframe=timeframe, candles=[]),
                        value_range=value_ranges(feature_id),
                    ),
                    live_compatible=leakage.live_compatible,
                    quarantined=False,
                    from_cache=True,
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
                    "computed": 0,
                    "reused": len(outcomes),
                    "quarantined": 0,
                },
            )
        )
        self._progress.on_set_end(outcomes)
        return FeatureSetComputationResult(
            set_name=feature_set.name,
            symbol=str(symbol),
            timeframe=str(timeframe),
            source_dataset_id=source_dataset_id,
            dataset_version=dataset_version,
            outcomes=outcomes,
        )

    def compute_set(
        self,
        feature_set: FeatureSet,
        symbol: Symbol,
        timeframe: Timeframe,
        candles: List[Candle],
        source_dataset_id: str,
        dataset_version: int,
        force: bool = False,
    ) -> FeatureSetComputationResult:
        """Compute every feature of ``feature_set`` over ``candles``.

        Stored features are reused when they were computed from exactly
        these candles and this catalogue. Pass ``force=True`` to
        recompute regardless.
        """
        context = FeatureInputContext(symbol=symbol, timeframe=timeframe, candles=candles)
        outcomes: List[FeatureComputationOutcome] = []
        total = len(feature_set.definitions)

        # Store the results for THIS series in their own directory when
        # the repository knows how to scope itself (Phase 37).
        repository = self._repository
        scoped = getattr(repository, "for_series", None)
        if callable(scoped):
            self._repository = scoped(str(symbol), str(timeframe))

        # Phase 38: reuse what is stored until the candles change.
        # Recursive indicators (EMA, MACD, ATR) carry state from the very
        # first candle, so a changed series means a FULL recompute — never
        # an append. The fingerprint decides; timestamps are not trusted.
        cache = FeatureCache(self._repository) if callable(scoped) else None
        reason = ""
        if cache is not None and not force:
            reason = cache.reason_to_recompute(candles, feature_set)
            if not reason:
                cached = cache.load_all(feature_set)
                if cached is not None:
                    self._progress.on_cache_hit(
                        set_name=feature_set.name,
                        symbol=str(symbol),
                        timeframe=str(timeframe),
                        total=total,
                    )
                    self._repository = repository
                    return self._result_from_cache(
                        feature_set,
                        symbol,
                        timeframe,
                        source_dataset_id,
                        dataset_version,
                        cached,
                    )

        self._progress.on_set_begin(
            set_name=feature_set.name,
            symbol=str(symbol),
            timeframe=str(timeframe),
            total=total,
            candles=len(candles),
            reason=reason or ("forced recompute" if force else ""),
        )

        try:
            for index, definition in enumerate(feature_set.definitions):
                self._progress.on_feature_begin(
                    index=index, total=total, feature_id=definition.feature_id.value
                )
                outcome = self.compute_feature(
                    definition=definition,
                    context=context,
                    source_dataset_id=source_dataset_id,
                    dataset_version=dataset_version,
                )
                outcomes.append(outcome)
                self._progress.on_feature_end(index=index, total=total, outcome=outcome)
            if cache is not None:
                cache.write_fingerprint(FeatureFingerprint.of(candles, feature_set))
        finally:
            self._repository = repository

        self._progress.on_set_end(outcomes)

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
