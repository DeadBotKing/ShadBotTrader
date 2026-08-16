"""Tests for the roll-forward (walk-forward) splitter."""

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.ai.roll_forward import (
    expanding_split,
    fold_slices,
    roll_forward_split,
)


def test_rolling_split_basic():
    plan = roll_forward_split(total_length=100, train_size=50, val_size=10, step=10)
    assert plan.fold_count == 5
    first = plan.folds[0]
    assert (first.train_start, first.train_end) == (0, 50)
    assert (first.val_start, first.val_end) == (50, 60)


def test_rolling_split_stops_at_end():
    plan = roll_forward_split(total_length=30, train_size=20, val_size=5, step=5)
    # folds: 0..20/20..25, 5..25/25..30, 10..30/30..35(no) -> 2 folds
    assert plan.fold_count == 2


def test_expanding_split_grows_training_window():
    plan = expanding_split(total_length=100, val_size=5, step=10, min_train_size=20)
    assert plan.folds[0].train_end == 20
    assert plan.folds[1].train_end == 30
    assert plan.folds[0].val_start == 20
    assert plan.folds[0].val_end == 25


def test_no_lookahead_in_folds():
    plan = expanding_split(total_length=50, val_size=5, step=5, min_train_size=10)
    for fold in plan.folds:
        assert fold.train_end <= fold.val_start  # train never touches validation


def test_invalid_sizes_raise():
    with pytest.raises(ValidationError):
        roll_forward_split(total_length=0, train_size=10, val_size=5, step=5)
    with pytest.raises(ValidationError):
        roll_forward_split(total_length=100, train_size=0, val_size=5, step=5)


def test_fold_slices():
    series = list(range(20))
    plan = roll_forward_split(total_length=20, train_size=10, val_size=5, step=5)
    train, val = fold_slices(series, plan.folds[0])
    assert list(train) == list(range(10))
    assert list(val) == list(range(10, 15))
