"""Framework-independent windowing of feature series into (window, target).

Mirrors the legacy ``window_dataset_signal_model``: a causal window of
``window_size`` feature rows is the model input and the last value of the
target column inside the window is the label. Features are min-max
scaled to [-2, 2] per window (as in the legacy implementation).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError


@dataclass(frozen=True)
class WindowedSample:
    """One (input, target) training/inference sample."""

    features: List[List[float]]
    target: Optional[float]
    target_index: int


def make_windows(
    series: Sequence[Sequence[float]],
    window_size: int,
    target_column: int,
    horizon: int = 0,
) -> List[WindowedSample]:
    """Build causal windows over ``series``.

    Each window holds ``window_size`` consecutive rows ending at index
    ``t``; the label is the value of ``target_column`` at index
    ``t + horizon`` (``horizon=0`` → the last row of the window). Only
    windows whose label lies inside the series are produced, so no
    lookahead happens for ``horizon=0``.
    """
    if window_size < 1:
        raise ValidationError("window_size must be >= 1")
    if target_column < 0 or target_column >= len(series[0]) if series else False:
        raise ValidationError("target_column out of range")

    samples: List[WindowedSample] = []
    n = len(series)
    for end in range(window_size - 1, n - horizon):
        window = [list(row) for row in series[end - window_size + 1 : end + 1]]
        target = series[end + horizon][target_column]
        samples.append(WindowedSample(features=window, target=target, target_index=target_column))
    return samples


def minmax_scale_window(
    window: List[List[float]], scale_range: tuple[float, float] = (-2.0, 2.0)
) -> List[List[float]]:
    """Min-max scale each feature column of a window into ``scale_range``.

    Per-column scaling over the window (matching the legacy behaviour).
    A constant column is mapped to the range midpoint.
    """
    if not window:
        return []
    low, high = scale_range
    n_cols = len(window[0])
    scaled = [[0.0] * n_cols for _ in window]
    for col in range(n_cols):
        values = [row[col] for row in window]
        minimum = min(values)
        maximum = max(values)
        span = maximum - minimum
        for row_index in range(len(window)):
            if span == 0:
                scaled[row_index][col] = (low + high) / 2.0
            else:
                ratio = (values[row_index] - minimum) / span
                scaled[row_index][col] = low + ratio * (high - low)
    return scaled


def build_samples(
    series: Sequence[Sequence[float]],
    window_size: int,
    target_column: int,
    scale: bool = True,
    horizon: int = 0,
) -> List[WindowedSample]:
    """Build windows and optionally min-max scale the feature columns."""
    samples = make_windows(series, window_size, target_column, horizon=horizon)
    if not scale:
        return samples
    return [
        WindowedSample(
            features=minmax_scale_window(sample.features),
            target=sample.target,
            target_index=sample.target_index,
        )
        for sample in samples
    ]
