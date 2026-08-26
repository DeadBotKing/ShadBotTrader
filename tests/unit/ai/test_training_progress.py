"""Tests for the training progress reporting contract."""

import io

from ShadBotTrader.infrastructure.ai.training_progress import (
    ConsoleProgressReporter,
    EpochMetrics,
    FoldInfo,
    NullProgressReporter,
    TrainingPlanInfo,
    format_duration,
)


def _plan(total_folds: int = 3, epochs: int = 2) -> TrainingPlanInfo:
    return TrainingPlanInfo(
        model_id="gold_direction",
        model_version=1,
        total_folds=total_folds,
        epochs_per_fold=epochs,
        learning_rate=1.5e-4,
        batch_size=8,
        window_size=16,
        n_features=4,
        total_samples=280,
        seed=42,
        framework="tensorflow",
        framework_version="2.21.0",
    )


def _fold(index: int = 0, total: int = 3) -> FoldInfo:
    return FoldInfo(
        fold_index=index,
        total_folds=total,
        train_samples=64,
        val_samples=8,
        train_start=0,
        train_end=64,
        val_start=64,
        val_end=72,
    )


def test_plan_total_epochs():
    assert _plan(total_folds=5, epochs=3).total_epochs == 15


def test_fold_and_epoch_display_indices_are_one_based():
    assert _fold(index=0).human_index == 1
    assert EpochMetrics(epoch=0, total_epochs=2).human_epoch == 1


def test_format_duration_units():
    assert format_duration(45) == "45s"
    assert format_duration(90) == "1:30"
    assert format_duration(3725) == "1:02:05"
    assert format_duration(-1) == "--"


def test_null_reporter_is_silent_and_accepts_the_full_contract():
    reporter = NullProgressReporter()
    plan, fold = _plan(), _fold()
    reporter.on_train_begin(plan)
    reporter.on_fold_begin(fold)
    reporter.on_epoch_end(fold, EpochMetrics(epoch=0, total_epochs=2, loss=0.7))
    reporter.on_fold_end(fold, 0.69)
    reporter.on_train_end([0.69])


def test_console_reporter_reports_plan_epochs_and_progress():
    stream = io.StringIO()
    reporter = ConsoleProgressReporter(stream=stream)

    plan = _plan(total_folds=2, epochs=2)
    reporter.on_train_begin(plan)
    for index in range(2):
        fold = _fold(index=index, total=2)
        reporter.on_fold_begin(fold)
        for epoch in range(2):
            reporter.on_epoch_end(
                fold,
                EpochMetrics(
                    epoch=epoch,
                    total_epochs=2,
                    loss=0.70,
                    val_loss=0.69,
                    accuracy=0.51,
                    val_accuracy=0.50,
                    learning_rate=1.5e-4,
                ),
            )
        reporter.on_fold_end(fold, 0.69)
    reporter.on_train_end([0.69, 0.69])

    output = stream.getvalue()
    # the plan is announced
    assert "gold_direction v1" in output
    assert "learning rate  : 0.00015" in output
    assert "epochs / fold  : 2" in output
    assert "folds          : 2" in output
    assert "total epochs   : 4" in output
    assert "tensorflow 2.21.0" in output
    # per-epoch metrics are visible (فاز ۵۳: قالب `key=value` بدون lr در epoch)
    assert "epoch   1/2" in output
    assert "epoch   2/2" in output
    assert "loss=0.7000" in output
    assert "val_loss=0.6900" in output
    # the fold completion is reported
    assert "fold   1/2" in output
    assert "OK fold 2/2 done" in output
    # the summary is printed
    assert "val_loss last:" in output
    assert "total time" in output


def test_console_reporter_can_hide_epoch_lines():
    stream = io.StringIO()
    reporter = ConsoleProgressReporter(stream=stream, show_epochs=False)

    fold = _fold(index=0, total=1)
    reporter.on_train_begin(_plan(total_folds=1))
    reporter.on_fold_begin(fold)
    reporter.on_epoch_end(fold, EpochMetrics(epoch=0, total_epochs=2, loss=0.7))
    reporter.on_fold_end(fold, 0.69)
    reporter.on_train_end([0.69])

    output = stream.getvalue()
    assert "epoch 1/2" not in output
    # the fold-level completion is still shown
    assert "OK fold" in output


def test_console_reporter_handles_missing_metrics():
    stream = io.StringIO()
    reporter = ConsoleProgressReporter(stream=stream)
    fold = _fold(index=0, total=1)

    reporter.on_train_begin(_plan(total_folds=1))
    reporter.on_fold_begin(fold)
    reporter.on_epoch_end(fold, EpochMetrics(epoch=0, total_epochs=1))
    reporter.on_fold_end(fold, 0.5)
    reporter.on_train_end([0.5])

    # placeholders instead of a crash
    assert "--" in stream.getvalue()
