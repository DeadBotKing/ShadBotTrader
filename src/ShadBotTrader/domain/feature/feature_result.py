"""Computed feature results (Phase 12, section 9)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from ShadBotTrader.domain.market.timestamp import Timestamp


@dataclass(frozen=True)
class FeaturePoint:
    """A single feature value aligned to one candle timestamp.

    ``value`` is ``None`` while the feature is inside its warmup window
    (not yet available). A non-``None`` value means the feature is
    available at ``timestamp``.
    """

    timestamp: Timestamp
    value: Optional[float]


@dataclass(frozen=True)
class FeatureResult:
    """The output of one feature computation over a candle series.

    ``points`` is aligned with the input candles. ``warmup`` records how
    many leading points were unavailable by construction (lookback).
    """

    feature_id: str
    points: List[FeaturePoint]
    warmup: int = 0

    @property
    def available_count(self) -> int:
        """Number of points with a non-``None`` value."""
        return sum(1 for point in self.points if point.value is not None)

    @property
    def missing_after_warmup(self) -> int:
        """Number of unavailable points that appear after the warmup."""
        return sum(1 for point in self.points[self.warmup :] if point.value is None)

    def values_after_warmup(self) -> List[float]:
        """The available values that follow the warmup window."""
        return [point.value for point in self.points[self.warmup :] if point.value is not None]
