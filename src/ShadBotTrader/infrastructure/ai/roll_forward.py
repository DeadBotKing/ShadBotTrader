"""Walk-forward (roll-forward) splitting for time-series training.

Roll-forward is the canonical time-series evaluation strategy: the model
trains on a rolling window and validates on the window that immediately
follows, then the window advances. No future data ever leaks into the
training window (Phase 13, sections 32, 46-47).
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


@dataclass(frozen=True)
class RollForwardPlan:
    """The full roll-forward split plan for a series length."""

    total_length: int
    train_size: int
    val_size: int
    step: int
    folds: tuple[Fold, ...]

    @property
    def fold_count(self) -> int:
        return len(self.folds)


def roll_forward_split(
    total_length: int,
    train_size: int,
    val_size: int,
    step: int,
    min_train_size: int = 1,
) -> RollForwardPlan:
    """Build a walk-forward plan.

    Each fold trains on ``[start, train_end)`` and validates on
    ``[train_end, train_end + val_size)``. The window then advances by
    ``step``. Folds whose training window is smaller than
    ``min_train_size`` or whose validation window runs past the end are
    dropped.
    """
    if total_length < 1:
        raise ValidationError("total_length must be >= 1")
    if train_size < 1 or val_size < 1:
        raise ValidationError("train_size and val_size must be >= 1")
    if step < 1:
        raise ValidationError("step must be >= 1")

    folds: List[Fold] = []
    start = 0
    fold_index = 0
    while True:
        train_end = start + train_size
        val_end = train_end + val_size
        if val_end > total_length:
            break
        if train_size < min_train_size:
            break
        folds.append(
            Fold(
                fold_index=fold_index,
                train_start=start,
                train_end=train_end,
                val_start=train_end,
                val_end=val_end,
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
    )


def expanding_split(
    total_length: int,
    val_size: int,
    step: int,
    min_train_size: int,
) -> RollForwardPlan:
    """Build an expanding-window variant (train grows, validation follows).

    The training window starts at ``min_train_size`` and grows by ``step``
    each fold; the validation window always sits right after it.
    """
    if total_length < 1 or val_size < 1 or step < 1 or min_train_size < 1:
        raise ValidationError("all sizes must be >= 1")

    folds: List[Fold] = []
    train_size = min_train_size
    fold_index = 0
    while True:
        train_end = train_size
        val_end = train_end + val_size
        if val_end > total_length:
            break
        folds.append(
            Fold(
                fold_index=fold_index,
                train_start=0,
                train_end=train_end,
                val_start=train_end,
                val_end=val_end,
            )
        )
        train_size += step
        fold_index += 1

    return RollForwardPlan(
        total_length=total_length,
        train_size=min_train_size,
        val_size=val_size,
        step=step,
        folds=tuple(folds),
    )


def fold_slices(series: Sequence, fold: Fold) -> tuple[Sequence, Sequence]:
    """Return the (train, validation) slices of ``series`` for a fold."""
    return series[fold.train_start : fold.train_end], series[fold.val_start : fold.val_end]
