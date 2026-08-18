"""Phase 42 — the epoch numbers survive all the way to the browser.

The operator's report, for the third time: "I still see nothing, in
PowerShell or on the web, showing each epoch's accuracy and error."

The progress lines WERE being produced and WERE reaching the log file.
They were being thrown away at the last step. Two causes:

**Batch chatter drowned the results.** One line per reported batch is
hundreds of lines per epoch. The dashboard reads a fixed tail of the
log, so the ticks filled the entire window and pushed every epoch result
out of it. Measured on a small run: 316 batch lines, and of the 200
lines the page could show, 158 were ticks.

**The in-place trick did not survive a pipe.** ``\\r`` overwrites a line
on a terminal; through a subprocess pipe into a file it is just a
character, so every "update" became a new permanent line. That is what
made the flood so much worse than intended.
"""

from ShadBotTrader.infrastructure.ai.training_progress import (
    ConsoleProgressReporter,
    EpochMetrics,
    FoldInfo,
)
from ShadBotTrader.presentation.commands.handlers import read_run_log, run_log_path

FOLD = FoldInfo(
    fold_index=0,
    total_folds=2,
    train_samples=8000,
    val_samples=500,
    train_start=0,
    train_end=8000,
    val_start=8000,
    val_end=8500,
)


class TestBatchChatterIsBounded:
    def test_an_epoch_emits_only_a_handful_of_lines(self):
        import io

        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)

        # A realistic epoch: 6,000 batches, every one reported to us.
        for batch in range(6000):
            reporter.on_batch_end(FOLD, batch, 6000, {"loss": 0.5, "mae": 0.02})

        lines = [line for line in stream.getvalue().splitlines() if line.strip()]

        assert len(lines) <= ConsoleProgressReporter.BATCH_LINES_PER_EPOCH + 2
        assert len(lines) >= 2  # it must still show SOMETHING

    def test_the_last_batch_is_always_reported(self):
        """Finishing at 94% would look like it stalled."""
        import io

        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        for batch in range(500):
            reporter.on_batch_end(FOLD, batch, 500, {"loss": 0.1})

        assert "100.0%" in stream.getvalue()

    def test_progress_lines_carry_the_metrics(self):
        import io

        stream = io.StringIO()
        ConsoleProgressReporter(stream=stream).on_batch_end(
            FOLD, 0, 10, {"loss": 0.1234, "mae": 0.0456}
        )
        text = stream.getvalue()

        assert "loss 0.1234" in text
        assert "mae 0.0456" in text

    def test_no_carriage_returns_reach_the_log(self):
        r"""``\r`` only works on a terminal; a pipe keeps it as a character."""
        import io

        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.on_batch_end(FOLD, 0, 10, {"loss": 0.1})
        reporter.on_epoch_end(FOLD, EpochMetrics(epoch=0, total_epochs=1, loss=0.1, val_loss=0.2))

        assert "\r" not in stream.getvalue()

    def test_zero_batches_is_not_a_crash(self):
        import io

        stream = io.StringIO()
        ConsoleProgressReporter(stream=stream).on_batch_end(FOLD, 0, 0, {})

        assert stream.getvalue() == ""


class TestTheDashboardKeepsTheResultLines:
    def write_log(self, tmp_path, epochs: int = 6, ticks_per_epoch: int = 400):
        """A log shaped like a real run: far more ticks than results."""
        path = run_log_path("train_dual_models", tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = ["$ scripts/run_dual_models.py --model range", "  TRAINING  gold_range_1d v1"]
        for epoch in range(epochs):
            for tick in range(ticks_per_epoch):
                lines.append(f"    [####----] {tick}% | batch {tick}/400 | loss 0.5")
            lines.append(f"  epoch {epoch + 1}/{epochs} | loss 0.10 | val_loss 0.09 | lr 1.5e-04")
        lines.append("  SAVED  gold_range_1d v1")
        path.write_text("\n".join(lines), encoding="utf-8")
        return path

    def test_every_epoch_line_survives_the_tail(self, tmp_path):
        """The bug: 2,400 ticks pushed all six epoch lines out of view."""
        self.write_log(tmp_path)

        visible = read_run_log("train_dual_models", tmp_path, lines=200)

        epochs = [line for line in visible if line.strip().startswith("epoch")]
        assert len(epochs) == 6, f"only {len(epochs)} of 6 epoch lines visible"

    def test_the_saved_confirmation_survives(self, tmp_path):
        self.write_log(tmp_path)

        visible = read_run_log("train_dual_models", tmp_path, lines=200)

        assert any("SAVED" in line for line in visible)

    def test_the_window_size_is_respected(self, tmp_path):
        self.write_log(tmp_path)

        visible = read_run_log("train_dual_models", tmp_path, lines=200)

        assert len(visible) <= 200

    def test_a_short_log_is_returned_whole(self, tmp_path):
        path = run_log_path("train_dual_models", tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("one\ntwo\nthree", encoding="utf-8")

        assert read_run_log("train_dual_models", tmp_path, lines=200) == ["one", "two", "three"]

    def test_errors_are_never_thinned_away(self, tmp_path):
        path = run_log_path("train_dual_models", tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"    [##] {i}% | batch {i}/900 | loss 0.5" for i in range(900)]
        lines.insert(5, "  [X] No stored candles for XAUUSD 1D.")
        path.write_text("\n".join(lines), encoding="utf-8")

        visible = read_run_log("train_dual_models", tmp_path, lines=200)

        assert any("[X]" in line for line in visible)

    def test_the_most_recent_lines_always_survive(self, tmp_path):
        path = run_log_path("train_dual_models", tmp_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = [f"    [##] {i}% | batch {i}/900 | loss 0.5" for i in range(900)]
        lines.append("  the very last thing that happened")
        path.write_text("\n".join(lines), encoding="utf-8")

        visible = read_run_log("train_dual_models", tmp_path, lines=200)

        assert visible[-1] == "  the very last thing that happened"

    def test_a_missing_log_is_empty_not_an_error(self, tmp_path):
        assert read_run_log("never_ran", tmp_path) == []


class TestTheReporterIsStillWiredIn:
    def test_the_trainer_reports_epochs_and_batches(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / "src/ShadBotTrader/infrastructure/ai/wavenet/wavenet_trainer.py"
        ).read_text(encoding="utf-8")

        assert "keras_progress_callback" in source
        assert "keras_batch_callback" in source

    def test_an_older_reporter_without_batch_support_still_works(self):
        """Observation must never be able to break training."""
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import _notify

        class Old:
            def __init__(self):
                self.seen = []

            def on_train_begin(self, plan):
                self.seen.append("begin")

        reporter = Old()
        _notify(reporter, "on_prepare_begin", 100, 32)  # absent -> skipped
        _notify(reporter, "on_train_begin", None)

        assert reporter.seen == ["begin"]
