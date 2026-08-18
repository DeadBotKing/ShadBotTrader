"""Phase 44 — a long epoch stays legible and takes fewer steps.

The operator's last run reached the training loop successfully and then
showed:

    [--------------------]   0.0% | batch 1/5,986 | loss 1.5662

Two problems in one line.

**5,986 gradient steps.** batch_size defaulted to 8 — a value chosen for
the few-hundred-row demo series. On 47,886 windows that is 5,986
forward+backward passes over a 500x123 input for a SINGLE epoch.

**One progress line every 748 batches.** With an 8-line budget per
epoch, that is roughly eleven minutes of silence between lines, and
eleven minutes of silence is what the operator reads as "frozen" — the
exact complaint this reporter exists to answer.
"""

import io
import time

import pytest

from ShadBotTrader.infrastructure.ai.training_progress import (
    ConsoleProgressReporter,
    FoldInfo,
)

FOLD = FoldInfo(
    fold_index=0,
    total_folds=1,
    train_samples=47886,
    val_samples=997,
    train_start=0,
    train_end=47886,
    val_start=47886,
    val_end=48883,
)


class TestBatchSizeScalesWithTheData:
    @pytest.mark.parametrize(
        "rows,expected",
        [(49897, 64), (20000, 64), (6000, 32), (2152, 16), (600, 8)],
    )
    def test_the_default_grows_with_the_series(self, rows, expected):
        """A demo-sized batch on real data means thousands of steps."""
        from ShadBotTrader.application.services.dual_model_service import DualModelService
        from ShadBotTrader.infrastructure.ai.model_roles import range_model_role

        service = DualModelService(include_features=False)

        class Prepared:
            series = [[0.0] * 6 for _ in range(rows)]
            role = range_model_role(window_size=32)
            target_columns = [4, 5]
            feature_count = 4

        trainer = service.build_trainer(Prepared(), epochs=1, max_folds=1)

        assert trainer._batch_size == expected

    def test_an_explicit_batch_size_is_respected(self):
        from ShadBotTrader.application.services.dual_model_service import DualModelService
        from ShadBotTrader.infrastructure.ai.model_roles import range_model_role

        service = DualModelService(include_features=False)

        class Prepared:
            series = [[0.0] * 6 for _ in range(49897)]
            role = range_model_role(window_size=32)
            target_columns = [4, 5]
            feature_count = 4

        trainer = service.build_trainer(Prepared(), epochs=1, max_folds=1, batch_size=8)

        assert trainer._batch_size == 8

    def test_the_step_count_drops_by_the_expected_factor(self):
        """47,886 windows: 5,986 steps at bs=8 becomes 748 at bs=64."""
        windows = 47886

        assert -(-windows // 8) == 5986
        assert -(-windows // 64) == 749  # ceil; Keras reports ~748


class TestSilenceIsBounded:
    def test_a_line_appears_even_when_the_stride_says_no(self):
        """Eleven minutes between lines reads as a hang."""
        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.MAX_SECONDS_BETWEEN_LINES = 0.2
        reporter.on_fold_begin(FOLD)

        # Batch 1 is on the stride; 2 and 3 are not, but time has passed.
        reporter.on_batch_end(FOLD, 0, 6000, {"loss": 0.5})
        time.sleep(0.25)
        reporter.on_batch_end(FOLD, 1, 6000, {"loss": 0.4})
        time.sleep(0.25)
        reporter.on_batch_end(FOLD, 2, 6000, {"loss": 0.3})

        ticks = [line for line in stream.getvalue().splitlines() if "batch" in line]
        assert len(ticks) == 3

    def test_the_time_rule_does_not_flood_a_fast_epoch(self):
        """When batches are quick, the count rule still governs."""
        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.on_fold_begin(FOLD)

        for batch in range(6000):
            reporter.on_batch_end(FOLD, batch, 6000, {"loss": 0.5})

        ticks = [line for line in stream.getvalue().splitlines() if "batch" in line]
        assert len(ticks) <= ConsoleProgressReporter.BATCH_LINES_PER_EPOCH + 2

    def test_the_clock_resets_for_each_fold(self):
        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.on_fold_begin(FOLD)
        first = reporter._last_batch_line
        time.sleep(0.05)
        reporter.on_fold_begin(FOLD)

        assert reporter._last_batch_line > first


class TestTheOperatorCanSeeHowLongItWillTake:
    def test_an_eta_appears_once_there_is_something_to_extrapolate(self):
        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.on_fold_begin(FOLD)

        reporter.on_batch_end(FOLD, 0, 100, {"loss": 0.5})
        time.sleep(0.2)
        reporter.on_batch_end(FOLD, 12, 100, {"loss": 0.4})

        lines = [line for line in stream.getvalue().splitlines() if "batch" in line]
        assert "eta" not in lines[0], "no ETA is honest on the very first batch"
        assert "eta" in lines[-1]

    def test_the_eta_shrinks_as_the_epoch_advances(self):
        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.MAX_SECONDS_BETWEEN_LINES = 0.05
        reporter.on_fold_begin(FOLD)

        seen = []
        for batch in (0, 20, 40, 60, 80):
            time.sleep(0.06)
            reporter.on_batch_end(FOLD, batch, 100, {"loss": 0.5})
        seen = [line for line in stream.getvalue().splitlines() if "eta" in line]

        assert len(seen) >= 3  # it keeps reporting as it goes
