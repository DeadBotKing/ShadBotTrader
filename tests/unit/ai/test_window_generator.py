"""Tests for stride-1 window generation (Phase 30 §3).

The user requirement is precise: roll-forward advances one candle at a
time across 500-row windows. Two things must hold — the arithmetic of
which rows belong to which window, and the fact that the windows are
never all held in memory at once.
"""

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.ai.window_generator import (
    DEFAULT_WINDOW_SIZE,
    WindowGenerator,
    plan_windows,
)


def series(rows: int, features: int = 3, targets: int = 2):
    """Rows whose values encode their own index, so alignment is checkable."""
    return [
        [float(index * 10 + column) for column in range(features)]
        + [float(index * 100 + offset) for offset in range(targets)]
        for index in range(rows)
    ]


# ----------------------------------------------------------------- plan ---
class TestWindowPlan:
    def test_the_default_window_is_the_five_hundred_the_user_asked_for(self):
        assert DEFAULT_WINDOW_SIZE == 500

    def test_stride_one_yields_one_window_per_candle(self):
        plan = plan_windows(total_rows=1000, window_size=500, horizon=5, stride=1)
        assert plan.window_count == 1000 - 500 - 5 + 1

    def test_a_larger_stride_yields_proportionally_fewer_windows(self):
        one = plan_windows(total_rows=1000, window_size=500, horizon=5, stride=1)
        five = plan_windows(total_rows=1000, window_size=500, horizon=5, stride=5)
        assert five.window_count == pytest.approx(one.window_count / 5, abs=1)

    def test_consecutive_windows_advance_exactly_one_row(self):
        plan = plan_windows(total_rows=1000, window_size=500, horizon=5, stride=1)
        assert plan.start_of(1) - plan.start_of(0) == 1
        assert plan.start_of(10) - plan.start_of(9) == 1

    def test_the_label_sits_one_horizon_past_the_window_end(self):
        plan = plan_windows(total_rows=1000, window_size=500, horizon=5, stride=1)
        assert plan.label_row_of(0) == 499 + 5
        assert plan.label_row_of(3) == 3 + 499 + 5

    def test_a_series_shorter_than_the_window_yields_nothing(self):
        plan = plan_windows(total_rows=100, window_size=500, horizon=5)
        assert plan.window_count == 0
        assert plan.is_empty

    def test_the_hundred_thousand_case_is_reported_honestly(self):
        """The number that forced the lazy design."""
        plan = plan_windows(
            total_rows=100_000, window_size=500, horizon=5, stride=1, feature_columns=123
        )
        assert plan.window_count == 99_496
        # materialising every window would need tens of GB
        assert plan.materialised_bytes() > 20e9
        # the flat matrix it comes from is trivial
        assert plan.flat_bytes() < 100e6

    def test_stride_zero_is_refused(self):
        with pytest.raises(ValidationError):
            plan_windows(total_rows=1000, stride=0)

    def test_an_out_of_range_window_raises(self):
        plan = plan_windows(total_rows=600, window_size=500, horizon=5)
        with pytest.raises(IndexError):
            plan.start_of(plan.window_count)


# ------------------------------------------------------------ generator ---
class TestWindowGenerator:
    def generator(self, rows=20, window=5, horizon=2, stride=1, **kwargs):
        return WindowGenerator(
            series(rows),
            target_columns=[3, 4],
            window_size=window,
            horizon=horizon,
            stride=stride,
            scale=False,
            **kwargs,
        )

    def test_targets_are_stripped_from_the_model_input(self):
        """R3 again: a window must not contain its own answer."""
        generator = self.generator()
        window, _ = generator.window_at(0)

        assert generator.input_shape == (5, 3)
        assert all(len(row) == 3 for row in window)

    def test_window_zero_covers_the_first_rows(self):
        window, label = self.generator().window_at(0)

        assert window[0][0] == 0.0  # row 0
        assert window[-1][0] == 40.0  # row 4
        assert label == [600.0, 601.0]  # row 4 + horizon 2 = row 6

    def test_window_one_has_advanced_exactly_one_candle(self):
        generator = self.generator()
        first, _ = generator.window_at(0)
        second, label = generator.window_at(1)

        assert second[0][0] == 10.0  # starts one row later
        assert second[:-1] == first[1:]  # overlaps by window-1 rows
        assert label == [700.0, 701.0]

    def test_iterating_yields_every_window_once(self):
        generator = self.generator()
        assert len(list(generator.iter_windows())) == generator.window_count

    def test_batches_have_the_right_shape(self):
        generator = self.generator(rows=40, window=5, horizon=2)
        x, y = next(generator.iter_batches(batch_size=4))

        assert x.shape == (4, 5, 3)
        assert y.shape == (4, 2)

    def test_the_final_batch_may_be_short_and_is_still_yielded(self):
        generator = self.generator(rows=20, window=5, horizon=2)
        batches = list(generator.iter_batches(batch_size=7))

        total = sum(batch[0].shape[0] for batch in batches)
        assert total == generator.window_count

    def test_classification_labels_come_back_as_integers(self):
        generator = WindowGenerator(
            series(20),
            target_columns=[3],
            window_size=5,
            horizon=2,
            scale=False,
            classification=True,
        )
        _, y = next(generator.iter_batches(batch_size=4))

        assert y.dtype.name == "int32"
        assert y.ndim == 1

    def test_scaling_is_applied_per_window_in_isolation(self):
        """A window must not learn anything from outside itself."""
        generator = WindowGenerator(
            series(20), target_columns=[3, 4], window_size=5, horizon=2, scale=True
        )
        window, _ = generator.window_at(0)
        flat = [value for row in window for value in row]

        assert min(flat) >= -2.0001
        assert max(flat) <= 2.0001

    def test_the_last_window_ignores_the_horizon(self):
        """At decision time the future does not exist yet."""
        generator = self.generator(rows=20, window=5, horizon=2)
        window = generator.last_window()

        assert len(window) == 5
        assert window[-1][0] == 190.0  # the newest row, not horizon-shifted

    def test_last_window_refuses_when_there_is_not_enough_history(self):
        generator = WindowGenerator(
            series(3), target_columns=[3, 4], window_size=5, horizon=0, scale=False
        )
        with pytest.raises(ValidationError):
            generator.last_window()

    def test_an_empty_series_is_refused(self):
        with pytest.raises(ValidationError):
            WindowGenerator([], target_columns=[0])

    def test_a_target_column_outside_the_matrix_is_refused(self):
        with pytest.raises(ValidationError):
            WindowGenerator(series(10), target_columns=[99])
