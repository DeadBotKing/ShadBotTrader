"""Lazy stride-1 windows over a flat feature matrix (Phase 30 §3).

The models consume ``(500, 123)`` inputs and the roll-forward advances
**one candle at a time**, so window ``k`` covers rows ``k .. k+499`` and
overlaps its neighbour by 499 rows.

Materialising those windows is not an option::

    99,495 windows x 500 rows x 123 cols x 4 bytes = 24.5 GB
    the flat matrix it all comes from              = 46 MB

So windows are produced on demand, batch by batch, and the 46 MB matrix
is the only thing ever held. This is not an optimisation — without it
the feature simply cannot run.

Scaling matches the rest of the AI platform: each window is min-max
scaled per column, in isolation, so a window never learns anything from
data outside itself.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterator, List, Optional, Sequence, Tuple

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window

#: The window height the user specified for both models.
DEFAULT_WINDOW_SIZE = 500


@dataclass(frozen=True)
class WindowPlan:
    """How many windows a series yields, and where each one sits.

    Computed arithmetically — never by building the windows first.
    """

    total_rows: int
    window_size: int
    horizon: int
    stride: int
    feature_columns: int
    target_columns: Tuple[int, ...]

    @property
    def window_count(self) -> int:
        """Windows that have a complete input *and* a real label."""
        usable = self.total_rows - self.window_size - self.horizon + 1
        if usable <= 0:
            return 0
        return (usable + self.stride - 1) // self.stride

    @property
    def is_empty(self) -> bool:
        return self.window_count == 0

    def start_of(self, index: int) -> int:
        """First matrix row of window ``index``."""
        if index < 0 or index >= self.window_count:
            raise IndexError(f"window {index} out of range (have {self.window_count})")
        return index * self.stride

    def label_row_of(self, index: int) -> int:
        """Matrix row whose label window ``index`` is trained against."""
        return self.start_of(index) + self.window_size - 1 + self.horizon

    def materialised_bytes(self) -> int:
        """What building every window at once *would* cost, for reporting."""
        return self.window_count * self.window_size * self.feature_columns * 4

    def flat_bytes(self) -> int:
        """What the lazy approach actually costs."""
        return self.total_rows * (self.feature_columns + len(self.target_columns)) * 4

    def describe(self) -> str:
        return (
            f"{self.window_count:,} windows of "
            f"({self.window_size} x {self.feature_columns}), stride {self.stride} — "
            f"lazy {self.flat_bytes() / 1e6:.0f} MB "
            f"vs materialised {self.materialised_bytes() / 1e9:.1f} GB"
        )


def plan_windows(
    total_rows: int,
    window_size: int = DEFAULT_WINDOW_SIZE,
    horizon: int = 5,
    stride: int = 1,
    feature_columns: int = 123,
    target_columns: Sequence[int] = (),
) -> WindowPlan:
    """Describe the windows a series of ``total_rows`` yields."""
    if window_size < 2:
        raise ValidationError("window_size must be >= 2")
    if horizon < 0:
        raise ValidationError("horizon must not be negative")
    if stride < 1:
        raise ValidationError("stride must be >= 1 (stride 1 = every candle)")
    return WindowPlan(
        total_rows=total_rows,
        window_size=window_size,
        horizon=horizon,
        stride=stride,
        feature_columns=feature_columns,
        target_columns=tuple(target_columns),
    )


class WindowGenerator:
    """Yields ``(X, y)`` batches from a flat labelled matrix, lazily.

    ``series`` holds feature columns first and target columns last, which
    is what :func:`attach_targets` produces. Target columns are stripped
    from the model input, so a window can never read its own answer.
    """

    def __init__(
        self,
        series: Sequence[Sequence[float]],
        target_columns: Sequence[int],
        window_size: int = DEFAULT_WINDOW_SIZE,
        horizon: int = 0,
        stride: int = 1,
        scale: bool = True,
        classification: bool = False,
    ) -> None:
        if not series:
            raise ValidationError("series must not be empty")
        if not target_columns:
            raise ValidationError("target_columns must not be empty")

        width = len(series[0])
        for column in target_columns:
            if column < 0 or column >= width:
                raise ValidationError(f"target column {column} out of range (width {width})")

        self._series = series
        self._targets = list(target_columns)
        self._keep = [index for index in range(width) if index not in set(target_columns)]
        self._window_size = window_size
        self._horizon = horizon
        self._stride = stride
        self._scale = scale
        self._classification = classification

        self.plan = plan_windows(
            total_rows=len(series),
            window_size=window_size,
            horizon=horizon,
            stride=stride,
            feature_columns=len(self._keep),
            target_columns=target_columns,
        )

    # ------------------------------------------------------------ shape --
    @property
    def window_count(self) -> int:
        return self.plan.window_count

    @property
    def feature_count(self) -> int:
        return len(self._keep)

    @property
    def input_shape(self) -> Tuple[int, int]:
        """The ``(rows, columns)`` shape every model input has."""
        return (self._window_size, len(self._keep))

    # ------------------------------------------------------------ access --
    def window_at(self, index: int) -> Tuple[List[List[float]], List[float]]:
        """Build exactly one ``(window, label)`` pair."""
        start = self.plan.start_of(index)
        stop = start + self._window_size

        window = [[float(row[column]) for column in self._keep] for row in self._series[start:stop]]
        if self._scale:
            window = minmax_scale_window(window)

        label_row = self._series[self.plan.label_row_of(index)]
        label = [float(label_row[column]) for column in self._targets]
        return window, label

    def iter_windows(
        self, start: int = 0, stop: Optional[int] = None
    ) -> Iterator[Tuple[List[List[float]], List[float]]]:
        """Yield ``(window, label)`` pairs one at a time."""
        last = self.window_count if stop is None else min(stop, self.window_count)
        for index in range(start, last):
            yield self.window_at(index)

    def iter_batches(
        self,
        batch_size: int = 32,
        start: int = 0,
        stop: Optional[int] = None,
    ) -> Iterator[Tuple[Any, Any]]:
        """Yield numpy ``(X, y)`` batches — the training entry point."""
        import numpy as np

        if batch_size < 1:
            raise ValidationError("batch_size must be >= 1")

        last = self.window_count if stop is None else min(stop, self.window_count)
        windows: List[List[List[float]]] = []
        labels: List[List[float]] = []

        for index in range(start, last):
            window, label = self.window_at(index)
            windows.append(window)
            labels.append(label)

            if len(windows) == batch_size:
                yield self._to_arrays(np, windows, labels)
                windows, labels = [], []

        if windows:
            yield self._to_arrays(np, windows, labels)

    def _to_arrays(self, np: Any, windows: List[Any], labels: List[Any]) -> Tuple[Any, Any]:
        x = np.array(windows, dtype=np.float32)
        if self._classification:
            # A single integer class per sample.
            y = np.array([int(label[0]) for label in labels], dtype=np.int32)
        else:
            y = np.array(labels, dtype=np.float32)
        return x, y

    # ---------------------------------------------------------- tf.data --
    def to_tf_dataset(self, batch_size: int = 32, start: int = 0, stop: Optional[int] = None):
        """A ``tf.data.Dataset`` streaming the same batches.

        Keeps TensorFlow out of the import path for every other caller.
        """
        import tensorflow as tf

        rows, columns = self.input_shape
        label_spec = (
            tf.TensorSpec(shape=(None,), dtype=tf.int32)
            if self._classification
            else tf.TensorSpec(shape=(None, len(self._targets)), dtype=tf.float32)
        )

        def generator():
            yield from self.iter_batches(batch_size=batch_size, start=start, stop=stop)

        return tf.data.Dataset.from_generator(
            generator,
            output_signature=(
                tf.TensorSpec(shape=(None, rows, columns), dtype=tf.float32),
                label_spec,
            ),
        ).prefetch(tf.data.AUTOTUNE)

    def last_window(self) -> List[List[float]]:
        """The most recent complete window — what live inference uses.

        Unlike :meth:`window_at` this ignores the horizon: at decision
        time the future does not exist yet, so there is no label to wait
        for. It is the newest 500 rows, scaled the same way training
        windows are.
        """
        if len(self._series) < self._window_size:
            raise ValidationError(
                f"Need {self._window_size} rows for a window; have {len(self._series)}."
            )
        rows = self._series[-self._window_size :]
        window = [[float(row[column]) for column in self._keep] for row in rows]
        return minmax_scale_window(window) if self._scale else window
