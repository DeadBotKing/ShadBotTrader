"""Builds labeled feature series from candles for AI training.

Framework-independent: produces a numeric feature matrix with a
classification target column (direction) ready for windowing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from ShadBotTrader.domain.market.candle import Candle


@dataclass(frozen=True)
class LabeledSeries:
    """A numeric feature matrix plus the target column index."""

    series: List[List[float]]
    target_column: int
    feature_names: List[str]


def build_direction_series(candles: Sequence[Candle]) -> LabeledSeries:
    """Build a direction-labeled feature matrix from candles.

    Feature columns (per row):

    * ``return_1``   — close-to-close 1-step return
    * ``range_pct``  — (high - low) / close
    * ``body_pct``   — (close - open) / close
    * ``volume_log`` — log1p(volume)

    Target column: ``direction`` — 1 when the next candle closes higher
    than the current one, else 0. The final candle has no label and is
    dropped from the matrix (no lookahead).
    """
    feature_names = ["return_1", "range_pct", "body_pct", "volume_log"]
    import math

    rows: List[List[float]] = []
    for index in range(len(candles) - 1):
        candle = candles[index]
        next_candle = candles[index + 1]
        close = float(candle.close.amount)
        previous_close = float(candles[index - 1].close.amount) if index > 0 else close
        return_1 = (close - previous_close) / previous_close if previous_close else 0.0
        range_pct = (float(candle.high.amount) - float(candle.low.amount)) / close if close else 0.0
        body_pct = (close - float(candle.open.amount)) / close if close else 0.0
        volume_log = math.log1p(float(candle.volume))
        direction = 1.0 if float(next_candle.close.amount) > close else 0.0
        rows.append([return_1, range_pct, body_pct, volume_log, direction])

    return LabeledSeries(
        series=rows,
        target_column=len(feature_names),
        feature_names=feature_names + ["direction"],
    )
