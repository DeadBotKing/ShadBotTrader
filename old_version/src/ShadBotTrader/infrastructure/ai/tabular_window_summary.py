"""Causal window-to-tabular summaries for booster model branches.

Neural WaveNet consumes the full ``[window, features]`` tensor. Tree
boosters such as LightGBM, CatBoost and XGBoost instead work best with a
flat tabular row. This module turns each causal model window into such a
row without looking past the sample end.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from ShadBotTrader.domain.common.errors import ValidationError

SUMMARY_MODES: tuple[str, ...] = ("last", "basic", "multi_scale")
DEFAULT_SCALES: tuple[int, ...] = (12, 48, 144, 288)


@dataclass(frozen=True)
class TabularWindowSummary:
    """Flat feature matrix built from sequential windows."""

    values: np.ndarray
    feature_names: list[str]
    sample_ends: list[int]

    @property
    def rows(self) -> int:
        return int(self.values.shape[0])

    @property
    def columns(self) -> int:
        return int(self.values.shape[1]) if self.values.ndim == 2 else 0


def _normalise_scales(scales: Sequence[int], window_size: int) -> list[int]:
    seen: list[int] = []
    for raw in scales:
        scale = int(raw)
        if 1 < scale <= window_size and scale not in seen:
            seen.append(scale)
    if window_size not in seen:
        seen.append(window_size)
    return seen


def _feature_labels(base_names: Sequence[str], suffix: str) -> list[str]:
    return [f"{name}__{suffix}" for name in base_names]


def _rolling_mean_std(
    values: np.ndarray,
    starts: np.ndarray,
    stops: np.ndarray,
    width: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Trailing mean/std for many windows using cumulative sums."""

    prefix = np.vstack(
        [np.zeros((1, values.shape[1]), dtype=np.float64), np.cumsum(values, axis=0)]
    )
    prefix_sq = np.vstack(
        [np.zeros((1, values.shape[1]), dtype=np.float64), np.cumsum(values * values, axis=0)]
    )
    sums = prefix[stops] - prefix[starts]
    sums_sq = prefix_sq[stops] - prefix_sq[starts]
    mean = sums / float(width)
    variance = np.maximum((sums_sq / float(width)) - (mean * mean), 0.0)
    return mean.astype(np.float32), np.sqrt(variance).astype(np.float32)


def summarise_windows(
    series: Sequence[Sequence[float]],
    feature_count: int,
    column_names: Sequence[str],
    sample_ends: Sequence[int],
    window_size: int,
    mode: str = "basic",
    scales: Sequence[int] = DEFAULT_SCALES,
) -> TabularWindowSummary:
    """Summarise each sequential window as one tabular booster row.

    Args:
        series: Prepared dataset rows; target columns may follow features.
        feature_count: Number of feature columns at the front of each row.
        column_names: Names of the feature columns in order.
        sample_ends: Row indices that end valid causal windows.
        window_size: Required model window length.
        mode: ``last`` only uses the final timestep; ``basic`` adds compact
            trailing statistics; ``multi_scale`` adds min/max/slope across
            multiple horizons.
        scales: Trailing window sizes, in rows/bars. Values larger than
            ``window_size`` are ignored.
    """

    if mode not in SUMMARY_MODES:
        raise ValidationError(f"Unknown summary mode {mode!r}; choose one of {SUMMARY_MODES}")
    if feature_count < 1:
        raise ValidationError("feature_count must be positive")
    if len(column_names) < feature_count:
        raise ValidationError("column_names must include every feature column")
    if window_size < 2:
        raise ValidationError("window_size must be >= 2")
    if not sample_ends:
        raise ValidationError("sample_ends must not be empty")

    features = np.asarray([list(row[:feature_count]) for row in series], dtype=np.float32)
    ends = np.asarray([int(value) for value in sample_ends], dtype=np.int64)
    if np.any(ends < window_size - 1):
        raise ValidationError("Every sample end must have a complete causal window behind it")
    if np.any(ends >= len(features)):
        raise ValidationError("sample_ends contains an index outside the series")

    base_names = list(column_names[:feature_count])
    pieces: list[np.ndarray] = []
    names: list[str] = []

    last = features[ends]
    pieces.append(last)
    names.extend(_feature_labels(base_names, "last"))

    if mode in ("basic", "multi_scale"):
        delta_1 = last - features[ends - 1]
        pieces.append(delta_1)
        names.extend(_feature_labels(base_names, "delta_1"))

        selected_scales = _normalise_scales(scales, window_size)
        if mode == "basic":
            selected_scales = [scale for scale in selected_scales if scale in (12, 48, window_size)]

        for scale in selected_scales:
            starts = ends - scale + 1
            stops = ends + 1
            mean, std = _rolling_mean_std(features, starts, stops, scale)
            pieces.extend([mean, std, last - features[starts]])
            names.extend(_feature_labels(base_names, f"mean_{scale}"))
            names.extend(_feature_labels(base_names, f"std_{scale}"))
            names.extend(_feature_labels(base_names, f"delta_{scale}"))

            if mode == "multi_scale":
                # Pandas' rolling min/max is implemented in C and is fast
                # enough for this research branch while keeping this module
                # simple and deterministic.
                import pandas as pd

                frame = pd.DataFrame(features)
                rolling = frame.rolling(window=scale, min_periods=scale)
                mins = rolling.min().to_numpy(dtype=np.float32)[ends]
                maxs = rolling.max().to_numpy(dtype=np.float32)[ends]
                slope = (last - features[starts]) / float(max(scale - 1, 1))
                pieces.extend([mins, maxs, slope])
                names.extend(_feature_labels(base_names, f"min_{scale}"))
                names.extend(_feature_labels(base_names, f"max_{scale}"))
                names.extend(_feature_labels(base_names, f"slope_{scale}"))

    matrix = np.concatenate(pieces, axis=1).astype(np.float32, copy=False)
    matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
    return TabularWindowSummary(matrix, names, ends.astype(int).tolist())
