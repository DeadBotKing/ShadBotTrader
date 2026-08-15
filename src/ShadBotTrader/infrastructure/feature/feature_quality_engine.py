"""Feature quality engine (Phase 12, sections 45-48)."""

from __future__ import annotations

import math
import statistics
from decimal import Decimal
from typing import List, Optional, Sequence

from ShadBotTrader.domain.feature.feature_quality import (
    FeatureIssueCode,
    FeatureQualityIssue,
    FeatureQualityReport,
    FeatureQualityScore,
)
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureInputContext


class FeatureQualityEngine:
    """Checks a computed feature for NaN/Inf/range/alignment problems.

    Checks performed:

    * ``EMPTY_RESULT`` — no input candles or no points
    * ``NAN_AFTER_WARMUP`` — unavailable values beyond the warmup window
    * ``INFINITE_VALUE`` — non-finite values in the result
    * ``OUT_OF_RANGE`` — values outside an expected [min, max] range
    * ``TIMESTAMP_MISALIGNED`` — point timestamps not aligned with input
    * ``DUPLICATE_TIMESTAMP`` — repeated timestamps in the result
    """

    def check(
        self,
        result: FeatureResult,
        context: FeatureInputContext,
        value_range: Optional[tuple[float, float]] = None,
    ) -> FeatureQualityReport:
        """Validate ``result`` against the input context and range."""
        issues: List[FeatureQualityIssue] = []

        if not result.points:
            return FeatureQualityReport(
                score=self._score(completeness=0, validity=0, stability=0, freshness=0),
                issues=[
                    FeatureQualityIssue(
                        FeatureIssueCode.EMPTY_RESULT, "Feature result has no points"
                    )
                ],
            )

        # timestamps alignment
        input_times = [candle.open_time.value for candle in context.candles]
        result_times = [point.timestamp.value for point in result.points]
        if len(result_times) != len(input_times) or any(
            left != right for left, right in zip(result_times, input_times, strict=False)
        ):
            issues.append(
                FeatureQualityIssue(
                    FeatureIssueCode.TIMESTAMP_MISALIGNED,
                    "Feature timestamps are not aligned with input candles",
                )
            )
        if len(set(result_times)) != len(result_times):
            issues.append(
                FeatureQualityIssue(
                    FeatureIssueCode.DUPLICATE_TIMESTAMP, "Duplicate timestamps in result"
                )
            )

        values_after = result.values_after_warmup()
        total_after_warmup = max(len(result.points) - result.warmup, 0)

        nan_after = result.missing_after_warmup
        if nan_after:
            issues.append(
                FeatureQualityIssue(
                    FeatureIssueCode.NAN_AFTER_WARMUP,
                    f"{nan_after} unavailable value(s) after warmup",
                    count=nan_after,
                )
            )

        inf_count = sum(1 for value in values_after if not math.isfinite(value))
        if inf_count:
            issues.append(
                FeatureQualityIssue(
                    FeatureIssueCode.INFINITE_VALUE,
                    f"{inf_count} non-finite value(s)",
                    count=inf_count,
                )
            )

        finite_values = [value for value in values_after if math.isfinite(value)]

        out_of_range = 0
        if finite_values and value_range is not None:
            low, high = value_range
            out_of_range = sum(1 for value in finite_values if value < low or value > high)
            if out_of_range:
                issues.append(
                    FeatureQualityIssue(
                        FeatureIssueCode.OUT_OF_RANGE,
                        f"{out_of_range} value(s) outside [{low}, {high}]",
                        count=out_of_range,
                    )
                )

        # score dimensions
        if total_after_warmup == 0:
            completeness = 0.0
        else:
            completeness = 100.0 * (1 - nan_after / total_after_warmup)

        validity = 100.0
        if finite_values:
            invalid = inf_count + out_of_range
            validity = 100.0 * (1 - invalid / max(len(finite_values), 1))
        elif not finite_values:
            validity = 0.0

        stability = self._stability(finite_values)
        freshness = 100.0 if total_after_warmup > 0 and not result.missing_after_warmup else 50.0

        return FeatureQualityReport(
            score=self._score(
                completeness=completeness,
                validity=validity,
                stability=stability,
                freshness=freshness,
            ),
            issues=issues,
        )

    @staticmethod
    def _stability(values: Sequence[float]) -> float:
        if len(values) < 2:
            return 100.0
        mean = statistics.fmean(values)
        if mean == 0:
            return 100.0
        std = statistics.pstdev(values)
        # coefficient of variation mapped to a 0..100 stability score
        cv = std / abs(mean)
        stability = 100.0 * (1 - min(cv, 1.0))
        return stability

    @staticmethod
    def _score(
        completeness: float,
        validity: float,
        stability: float,
        freshness: float,
    ) -> FeatureQualityScore:
        return FeatureQualityScore(
            completeness=Decimal(str(round(completeness, 2))),
            validity=Decimal(str(round(validity, 2))),
            stability=Decimal(str(round(stability, 2))),
            freshness=Decimal(str(round(freshness, 2))),
        )
