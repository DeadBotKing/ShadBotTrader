"""Purged fold geometry and aligned window-count tests."""

import numpy as np

from ShadBotTrader.application.services.dual_model_service import PreparedDataset
from ShadBotTrader.infrastructure.ai.model_roles import range_model_role
from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split


def test_variable_horizon_targets_are_removed_before_validation_input():
    # The third training candidate has a first-passage target ending at raw
    # coordinate 10.  The fold's validation input starts at coordinate 6,
    # so that candidate and every later candidate must be purged.
    sample_ends = list(range(3, 17))
    label_ends = [3, 4, 10, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16]
    plan = expanding_split(
        total_length=len(sample_ends),
        val_size=2,
        step=2,
        min_train_size=2,
        purge_gap=0,
        sample_end_indices=sample_ends,
        label_end_indices=label_ends,
        window_size=4,
    )

    assert plan.folds
    purged = [fold for fold in plan.folds if fold.purged_train_samples]
    assert purged
    for fold in purged:
        assert fold.validation_input_start is not None
        for index in range(fold.train_start, fold.train_end):
            assert sample_ends[index] < fold.validation_input_start
            assert label_ends[index] < fold.validation_input_start


def test_range_dataset_summary_does_not_subtract_horizon_twice():
    role = range_model_role(timeframe="1H", horizon=5, window_size=10)
    dataset = PreparedDataset(
        series=[[float(index)] * 3 for index in range(95)],
        column_names=["a", "b", "c"],
        target_columns=[2],
        role=role,
        feature_count=2,
        dropped_warmup=0,
    )

    # The series is already trimmed to rows with complete future labels.
    # WindowGenerator therefore yields 95 - 10 + 1, not another -5.
    assert dataset.summary()["training_windows"] == 86


def test_purged_range_geometry_has_no_shared_input_or_target_rows():
    window = 10
    horizon = 5
    total_samples = 120
    sample_ends = [window - 1 + index for index in range(total_samples)]
    label_ends = [end + horizon for end in sample_ends]
    plan = expanding_split(
        total_length=total_samples,
        val_size=8,
        step=8,
        min_train_size=30,
        purge_gap=window - 1 + horizon,
        sample_end_indices=sample_ends,
        label_end_indices=label_ends,
        window_size=window,
    )

    assert plan.folds
    for fold in plan.folds:
        val_input_start = sample_ends[fold.val_start] - window + 1
        for index in range(fold.train_start, fold.train_end):
            assert sample_ends[index] < val_input_start
            assert label_ends[index] < val_input_start


def test_range_metric_shape_can_be_split_into_two_bound_errors():
    # Small numerical guard for the diagnostic convention: prediction minus
    # truth, with high and low kept as separate columns.
    actual = np.array([[0.01, -0.02], [0.02, -0.01]])
    truth = np.array([[0.00, -0.01], [0.01, -0.02]])
    error = actual - truth
    assert np.mean(np.abs(error[:, 0])) == 0.01
    assert np.mean(np.abs(error[:, 1])) == 0.01
