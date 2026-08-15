"""Data-quality engine: gaps, duplicates and outliers (L3)."""

from __future__ import annotations

import statistics
from datetime import timedelta
from decimal import Decimal
from typing import List

from ShadBotTrader.domain.dataset.pipeline import QualityAnalyzerPort
from ShadBotTrader.domain.dataset.quality_report import (
    IssueSeverity,
    QualityIssue,
    QualityReport,
    QualityScore,
)
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.timeframe import Timeframe

_MAD_CONSTANT = 1.4826
_PRICE_OUTLIER_K = 8.0
_VOLUME_OUTLIER_K = 10.0


class QualityAnalyzer(QualityAnalyzerPort):
    """Analyses a normalized candle list and produces a QualityReport.

    Detected issues:

    * ``DUPLICATE_TIMESTAMP`` — multiple candles for the same open time
    * ``GAP_DETECTED`` — missing candle between two consecutive opens
    * ``PRICE_OUTLIER`` — close deviates from the robust median by > 8 MAD
    * ``VOLUME_OUTLIER`` — volume exceeds 10x the robust median

    Detection only flags data; nothing is deleted (Phase 11 section 38).
    """

    def analyze(self, candles: List[Candle], timeframe: Timeframe) -> QualityReport:
        """Compute the quality report for ``candles``."""
        if not candles:
            return QualityReport(
                score=QualityScore(
                    completeness=Decimal(0),
                    consistency=Decimal(0),
                    validity=Decimal(0),
                    timeliness=Decimal(0),
                    uniqueness=Decimal(0),
                ),
                issues=[
                    QualityIssue(
                        code="EMPTY_DATASET",
                        severity=IssueSeverity.CRITICAL,
                        message="Dataset contains no candles",
                    )
                ],
            )

        ordered = sorted(candles, key=lambda candle: candle.open_time.value)
        issues: List[QualityIssue] = []
        duplicate_count = self._duplicate_count(ordered)
        gap_count = self._gap_count(ordered, timeframe)
        price_outlier_count = self._price_outlier_count(ordered)
        volume_outlier_count = self._volume_outlier_count(ordered)

        total = len(ordered)
        if duplicate_count:
            issues.append(
                QualityIssue(
                    code="DUPLICATE_TIMESTAMP",
                    severity=IssueSeverity.WARNING,
                    message=f"{duplicate_count} candle(s) share a timestamp",
                    count=duplicate_count,
                )
            )
        if gap_count:
            issues.append(
                QualityIssue(
                    code="GAP_DETECTED",
                    severity=IssueSeverity.WARNING,
                    message=f"{gap_count} gap(s) found in the candle sequence",
                    count=gap_count,
                )
            )
        if price_outlier_count:
            issues.append(
                QualityIssue(
                    code="PRICE_OUTLIER",
                    severity=IssueSeverity.WARNING,
                    message=f"{price_outlier_count} candle(s) with abnormal price",
                    count=price_outlier_count,
                )
            )
        if volume_outlier_count:
            issues.append(
                QualityIssue(
                    code="VOLUME_OUTLIER",
                    severity=IssueSeverity.WARNING,
                    message=f"{volume_outlier_count} candle(s) with abnormal volume",
                    count=volume_outlier_count,
                )
            )

        score = self._score(
            total=total,
            duplicates=duplicate_count,
            gaps=gap_count,
            price_outliers=price_outlier_count,
            volume_outliers=volume_outlier_count,
        )
        return QualityReport(score=score, issues=issues)

    @staticmethod
    def _duplicate_count(candles: List[Candle]) -> int:
        seen: set = set()
        duplicates = 0
        for candle in candles:
            key = (str(candle.symbol), str(candle.timeframe), candle.open_time.value)
            if key in seen:
                duplicates += 1
            else:
                seen.add(key)
        return duplicates

    @staticmethod
    def _gap_count(candles: List[Candle], timeframe: Timeframe) -> int:
        step = _timeframe_delta(timeframe)
        gaps = 0
        for previous, current in zip(candles, candles[1:], strict=False):
            expected = previous.open_time.value + step
            if current.open_time.value > expected:
                gaps += 1
        return gaps

    @staticmethod
    def _price_outlier_count(candles: List[Candle]) -> int:
        closes = [float(candle.close.amount) for candle in candles]
        median = statistics.median(closes)
        mad = _mad(closes, median) or _fallback_scale(median)
        return sum(1 for close in closes if abs(close - median) > _PRICE_OUTLIER_K * mad)

    @staticmethod
    def _volume_outlier_count(candles: List[Candle]) -> int:
        volumes = [float(candle.volume) for candle in candles]
        median = statistics.median(volumes)
        if median == 0:
            return 0
        return sum(1 for volume in volumes if volume > _VOLUME_OUTLIER_K * median)

    @staticmethod
    def _score(
        total: int,
        duplicates: int,
        gaps: int,
        price_outliers: int,
        volume_outliers: int,
    ) -> QualityScore:
        def ratio(bad: int) -> Decimal:
            return Decimal(100) * (Decimal(1) - Decimal(min(bad, total)) / Decimal(total))

        uniqueness = ratio(duplicates)
        timeliness = ratio(gaps)
        consistency = ratio(price_outliers + volume_outliers)
        return QualityScore(
            completeness=Decimal(100),
            consistency=consistency,
            validity=Decimal(100),
            timeliness=timeliness,
            uniqueness=uniqueness,
        )


def _timeframe_delta(timeframe: Timeframe) -> timedelta:
    if timeframe.unit.value == "minute":
        return timedelta(minutes=timeframe.amount)
    if timeframe.unit.value == "hour":
        return timedelta(hours=timeframe.amount)
    return timedelta(days=timeframe.amount)


def _mad(values: List[float], median: float) -> float:
    deviations = [abs(value - median) for value in values]
    return statistics.median(deviations) * _MAD_CONSTANT


def _fallback_scale(median: float) -> float:
    return abs(median) * 0.3 + 1e-9
