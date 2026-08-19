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
    """One (input, target) training/inference sample.

    ``target`` carries the single label of the classification path.
    ``targets`` carries several continuous labels for the Phase 29
    regression head (future high and low offsets); it stays ``None`` for
    single-target callers so existing behaviour is untouched.
    """

    features: List[List[float]]
    target: Optional[float]
    target_index: int
    targets: Optional[List[float]] = None


def make_windows(
    series: Sequence[Sequence[float]],
    window_size: int,
    target_column: int,
    horizon: int = 0,
    drop_target_column: bool = False,
) -> List[WindowedSample]:
    """Build causal windows over ``series``.

    Each window holds ``window_size`` consecutive rows ending at index
    ``t``; the label is the value of ``target_column`` at index
    ``t + horizon`` (``horizon=0`` → the last row of the window). Only
    windows whose label lies inside the series are produced, so no
    lookahead happens for ``horizon=0``.

    Args:
        drop_target_column: when True the target column is removed from
            the feature rows. This is required for ``horizon=0``: the
            label would otherwise sit inside the last row of its own
            window, letting the model read the answer off its input
            (target leakage). Defaults to False to preserve the raw
            windowing semantics for callers that need every column.
    """
    if window_size < 1:
        raise ValidationError("window_size must be >= 1")
    if target_column < 0 or target_column >= len(series[0]) if series else False:
        raise ValidationError("target_column out of range")

    samples: List[WindowedSample] = []
    n = len(series)
    for end in range(window_size - 1, n - horizon):
        window = [list(row) for row in series[end - window_size + 1 : end + 1]]
        if drop_target_column:
            window = [row[:target_column] + row[target_column + 1 :] for row in window]
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


def build_samples_at(
    series: Sequence[Sequence[float]],
    window_size: int,
    target_column: int,
    sample_ends: Sequence[int],
    scale: bool = True,
    horizon: int = 0,
    drop_target_column: bool = False,
) -> List[WindowedSample]:
    """Build windows ending at explicit candle indices.

    This is used by first-passage signal labels: unlabeled starts may be
    absent, but every selected sample must still contain the real previous
    candles from the full feature matrix, not the previous labeled rows.
    """
    if window_size < 1:
        raise ValidationError("window_size must be >= 1")
    width = len(series[0]) if series else 0
    if target_column < 0 or target_column >= width:
        raise ValidationError("target_column out of range")

    samples: List[WindowedSample] = []
    for end in sample_ends:
        if end < window_size - 1 or end + horizon >= len(series):
            continue
        window = [list(row) for row in series[end - window_size + 1 : end + 1]]
        if drop_target_column:
            window = [row[:target_column] + row[target_column + 1 :] for row in window]
        samples.append(
            WindowedSample(
                features=minmax_scale_window(window) if scale else window,
                target=series[end + horizon][target_column],
                target_index=target_column,
            )
        )
    return samples


def build_samples(
    series: Sequence[Sequence[float]],
    window_size: int,
    target_column: int,
    scale: bool = True,
    horizon: int = 0,
    drop_target_column: bool = False,
) -> List[WindowedSample]:
    """Build windows and optionally min-max scale the feature columns."""
    samples = make_windows(
        series,
        window_size,
        target_column,
        horizon=horizon,
        drop_target_column=drop_target_column,
    )
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


def make_multi_target_windows(
    series: Sequence[Sequence[float]],
    window_size: int,
    target_columns: Sequence[int],
    horizon: int = 0,
) -> List[WindowedSample]:
    """Causal windows with several continuous targets (Phase 29).

    Used by the range model, which predicts two values at once (the
    future high and low offsets). Every target column is removed from
    the feature rows: the labels were pre-computed from future bars, so
    leaving them in the input would hand the model the answer.
    """
    if window_size < 1:
        raise ValidationError("window_size must be >= 1")
    if not target_columns:
        raise ValidationError("target_columns must not be empty")
    if not series:
        raise ValidationError("series must not be empty")

    width = len(series[0])
    for column in target_columns:
        if column < 0 or column >= width:
            raise ValidationError(f"target column {column} out of range (width {width})")

    drop = set(target_columns)
    keep = [index for index in range(width) if index not in drop]

    samples: List[WindowedSample] = []
    for end in range(window_size - 1, len(series) - horizon):
        window = [
            [float(row[index]) for index in keep] for row in series[end - window_size + 1 : end + 1]
        ]
        label_row = series[end + horizon]
        samples.append(
            WindowedSample(
                features=window,
                target=None,
                target_index=target_columns[0],
                targets=[float(label_row[column]) for column in target_columns],
            )
        )
    return samples


def build_multi_target_samples(
    series: Sequence[Sequence[float]],
    window_size: int,
    target_columns: Sequence[int],
    scale: bool = True,
    horizon: int = 0,
) -> List[WindowedSample]:
    """Multi-target windows, optionally min-max scaled per window.

    Only the *features* are scaled. The targets are already expressed as
    price fractions and must keep their real magnitude — rescaling them
    per window would make a 0.5% move and a 5% move look identical.
    """
    samples = make_multi_target_windows(series, window_size, target_columns, horizon=horizon)
    if not scale:
        return samples
    return [
        WindowedSample(
            features=minmax_scale_window(sample.features),
            target=sample.target,
            target_index=sample.target_index,
            targets=sample.targets,
        )
        for sample in samples
    ]
