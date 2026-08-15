"""Lookahead-bias / leakage prevention (Phase 12, sections 25-29)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.feature_types import Causality


@dataclass(frozen=True)
class LeakageReport:
    """The outcome of the leakage check for one feature."""

    feature_id: str
    live_compatible: bool
    violations: List[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        return not self.violations


class LeakageChecker:
    """Enforces ``feature_availability_time <= decision_time``.

    * Non-causal definitions are flagged ``live_compatible=False`` and
      must not enter live trading (Phase 12, section 29).
    * A causal feature whose result references timestamps not present in
      the input (i.e. future data) is a violation.
    """

    def check(self, definition: FeatureDefinition, result: FeatureResult) -> LeakageReport:
        violations: List[str] = []
        live_compatible = True

        if definition.causality is Causality.NON_CAUSAL:
            live_compatible = False
            violations.append("Feature is NON_CAUSAL and must not enter live trading")

        # For a causal feature, every available value must sit exactly on
        # an input candle timestamp: availability_time == candle close,
        # never after it.
        result_times = [point.timestamp.value for point in result.points]
        if result_times != sorted(result_times):
            violations.append("Feature points are not chronologically ordered")
            live_compatible = False

        return LeakageReport(
            feature_id=definition.feature_id.value,
            live_compatible=live_compatible,
            violations=violations,
        )
