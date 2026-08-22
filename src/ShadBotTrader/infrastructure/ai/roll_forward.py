"""Purged roll-forward (walk-forward) splitting for time-series training.

Roll-forward is the canonical time-series evaluation strategy: the model
trains on earlier observations and validates on the window that follows.
The optional purge metadata makes the stronger guarantee explicit:

* train input windows do not share candles with validation input windows;
* a training target cannot reach into the validation input interval.

The second rule matters for first-passage labels, whose lookahead is
variable and can be much longer than a fixed range horizon.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from ShadBotTrader.domain.common.errors import ValidationError


@dataclass(frozen=True)
class Fold:
    """One walk-forward fold: train range + the validation range after it."""

    fold_index: int
    train_start: int
    train_end: int
    val_start: int
    val_end: int
    #: Number of candidate training samples removed because their input or
    #: target reached the validation input interval.
    purged_train_samples: int = 0
    #: Raw row/candle coordinate at which the first validation input starts.
    validation_input_start: int | None = None


@dataclass(frozen=True)
class RollForwardPlan:
    """The full roll-forward split plan for a series length."""

    total_length: int
    train_size: int
    val_size: int
    step: int
    folds: tuple[Fold, ...]
    purge_gap: int = 0

    @property
    def fold_count(self) -> int:
        return len(self.folds)


def _validate_label_geometry(
    total_length: int,
    sample_end_indices: Sequence[int] | None,
    label_end_indices: Sequence[int] | None,
    window_size: int,
) -> None:
    if (sample_end_indices is None) != (label_end_indices is None):
        raise ValidationError("sample_end_indices and label_end_indices must be supplied together")
    if window_size < 1:
        raise ValidationError("window_size must be >= 1")
    if sample_end_indices is None:
        return
    if label_end_indices is None:  # narrowed for type-checkers
        raise ValidationError("label_end_indices must be supplied with sample_end_indices")
    if len(sample_end_indices) != total_length or len(label_end_indices) != total_length:
        raise ValidationError("purge metadata must have one entry per sample")
    if any(
        later <= earlier
        for earlier, later in zip(sample_end_indices, sample_end_indices[1:], strict=False)
    ):
        raise ValidationError("sample_end_indices must be strictly increasing")
    if any(
        label < start for start, label in zip(sample_end_indices, label_end_indices, strict=True)
    ):
        raise ValidationError("a target end cannot precede its sample end")


def _purged_train_end(
    train_start: int,
    candidate_train_end: int,
    val_start: int,
    sample_end_indices: Sequence[int] | None,
    label_end_indices: Sequence[int] | None,
    window_size: int,
) -> tuple[int, int | None]:
    """Trim the candidate train prefix at the first unsafe target/input."""
    if sample_end_indices is None or label_end_indices is None:
        return candidate_train_end, None
    validation_input_start = sample_end_indices[val_start] - window_size + 1
    safe_end = candidate_train_end
    for index in range(train_start, candidate_train_end):
        # A train window ending at/after the first validation input shares
        # at least one candle. A variable-horizon target reaching that same
        # point is also leakage even when the train input itself is old.
        if (
            sample_end_indices[index] >= validation_input_start
            or label_end_indices[index] >= validation_input_start
        ):
            safe_end = index
            break
    return safe_end, validation_input_start


def roll_forward_split(
    total_length: int,
    train_size: int,
    val_size: int,
    step: int,
    min_train_size: int = 1,
    purge_gap: int = 0,
    sample_end_indices: Sequence[int] | None = None,
    label_end_indices: Sequence[int] | None = None,
    window_size: int = 1,
) -> RollForwardPlan:
    """Build a rolling walk-forward plan.

    Each ordinary fold trains on ``[start, train_end)`` and validates on
    ``[val_start, val_end)``.  ``purge_gap`` is an embargo measured in
    sample positions, retained for backwards compatibility.  When raw
    sample/target coordinates are supplied, the train range is additionally
    trimmed so no train input or target reaches the first validation input.
    """
    if total_length < 1:
        raise ValidationError("total_length must be >= 1")
    if train_size < 1 or val_size < 1:
        raise ValidationError("train_size and val_size must be >= 1")
    if step < 1:
        raise ValidationError("step must be >= 1")
    if purge_gap < 0:
        raise ValidationError("purge_gap must be >= 0")
    _validate_label_geometry(total_length, sample_end_indices, label_end_indices, window_size)

    folds: List[Fold] = []
    start = 0
    fold_index = 0
    while True:
        candidate_train_end = start + train_size
        val_start = candidate_train_end + purge_gap
        val_end = val_start + val_size
        if val_end > total_length:
            break
        if train_size < min_train_size:
            break

        train_end, validation_input_start = _purged_train_end(
            start,
            candidate_train_end,
            val_start,
            sample_end_indices,
            label_end_indices,
            window_size,
        )
        purged = candidate_train_end - train_end
        if train_end - start < min_train_size:
            # A variable-horizon label can consume an entire candidate
            # training prefix. Dropping that fold is safer than reporting
            # a validation score trained with future information.
            start += step
            fold_index += 1
            continue

        folds.append(
            Fold(
                fold_index=fold_index,
                train_start=start,
                train_end=train_end,
                val_start=val_start,
                val_end=val_end,
                purged_train_samples=purged,
                validation_input_start=validation_input_start,
            )
        )
        start += step
        fold_index += 1

    return RollForwardPlan(
        total_length=total_length,
        train_size=train_size,
        val_size=val_size,
        step=step,
        folds=tuple(folds),
        purge_gap=purge_gap,
    )


def expanding_split(
    total_length: int,
    val_size: int,
    step: int,
    min_train_size: int,
    purge_gap: int = 0,
    sample_end_indices: Sequence[int] | None = None,
    label_end_indices: Sequence[int] | None = None,
    window_size: int = 1,
) -> RollForwardPlan:
    """Build an expanding-window variant (train grows, validation follows).

    The training window starts at ``min_train_size`` and grows by ``step``
    each fold.  With purge metadata, ``train_end`` can be shorter than the
    candidate boundary: the removed suffix contains labels whose future
    reaches into the validation input.  This is the important distinction
    between a merely chronological split and a purged split.
    """
    if total_length < 1 or val_size < 1 or step < 1 or min_train_size < 1:
        raise ValidationError("all sizes must be >= 1")
    if purge_gap < 0:
        raise ValidationError("purge_gap must be >= 0")
    _validate_label_geometry(total_length, sample_end_indices, label_end_indices, window_size)

    folds: List[Fold] = []
    candidate_train_end = min_train_size
    fold_index = 0
    while True:
        val_start = candidate_train_end + purge_gap
        val_end = val_start + val_size
        if val_end > total_length:
            break

        train_end, validation_input_start = _purged_train_end(
            0,
            candidate_train_end,
            val_start,
            sample_end_indices,
            label_end_indices,
            window_size,
        )
        purged = candidate_train_end - train_end
        if train_end < min_train_size:
            candidate_train_end += step
            fold_index += 1
            continue

        folds.append(
            Fold(
                fold_index=fold_index,
                train_start=0,
                train_end=train_end,
                val_start=val_start,
                val_end=val_end,
                purged_train_samples=purged,
                validation_input_start=validation_input_start,
            )
        )
        candidate_train_end += step
        fold_index += 1

    return RollForwardPlan(
        total_length=total_length,
        train_size=min_train_size,
        val_size=val_size,
        step=step,
        folds=tuple(folds),
        purge_gap=purge_gap,
    )


def fold_slices(series: Sequence, fold: Fold) -> tuple[Sequence, Sequence]:
    """Return the (train, validation) slices of ``series`` for a fold."""
    return series[fold.train_start : fold.train_end], series[fold.val_start : fold.val_end]
