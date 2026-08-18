"""Phase 46 — an interrupted run keeps its work, and the ETA is honest.

The operator lost a two-hour training run:

    FAILED: train_dual_models · 7205.5s
    Timed out after 120 minutes
    epoch 18/20 | loss 0.5102 | val_loss 0.5279 | acc 0.8181 | val_acc 0.7994

Eighteen completed epochs, a model that was still improving, and nothing
saved — because the artifact was only written after ``train()`` returned.
The 7,200-second limit killed it during epoch 19.

The same log showed a second defect:

    batch 105/468 ... eta 2:58:40      (the epoch finished ~4 minutes later)

The ETA divided the whole FOLD's elapsed time by the CURRENT EPOCH's
batch count. By epoch 19 the fold had been running two hours, so the
estimate was roughly forty-five times too large.
"""

import io
import time

import pytest

from ShadBotTrader.infrastructure.ai.training_progress import (
    ConsoleProgressReporter,
    EpochMetrics,
    FoldInfo,
)
from ShadBotTrader.presentation.commands.commands import CommandKind
from ShadBotTrader.presentation.commands.handlers import descriptors

FOLD = FoldInfo(
    fold_index=0,
    total_folds=1,
    train_samples=30000,
    val_samples=997,
    train_start=0,
    train_end=30000,
    val_start=30000,
    val_end=30997,
)


class TestTheEtaIsMeasuredPerEpoch:
    def test_a_later_epoch_does_not_inherit_earlier_elapsed_time(self):
        """The bug: eta 2:58:40 when four minutes remained."""
        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.MAX_SECONDS_BETWEEN_LINES = 0.01
        reporter.on_fold_begin(FOLD)

        # A slow first epoch.
        for batch in (0, 50, 100):
            time.sleep(0.05)
            reporter.on_batch_end(FOLD, batch, 468, {"loss": 0.5})
        reporter.on_epoch_end(FOLD, EpochMetrics(epoch=0, total_epochs=20, loss=0.5, val_loss=0.53))

        # A long gap, then a fast second epoch.
        time.sleep(0.4)
        stream.truncate(0)
        stream.seek(0)
        for batch in (0, 50):
            time.sleep(0.01)
            reporter.on_batch_end(FOLD, batch, 468, {"loss": 0.49})

        lines = [line for line in stream.getvalue().splitlines() if "eta" in line]
        assert lines, "the second epoch should still report an ETA"
        # Seconds, not hours. The bug produced "eta 2:58:40" here because
        # it carried the first epoch's elapsed time forward.
        assert ":" not in lines[-1].split("eta ")[1], lines[-1]

    def test_the_epoch_clock_resets_at_each_epoch_boundary(self):
        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.on_fold_begin(FOLD)
        first = reporter._epoch_start

        time.sleep(0.05)
        reporter.on_epoch_end(FOLD, EpochMetrics(epoch=0, total_epochs=5, loss=0.5, val_loss=0.5))

        assert reporter._epoch_start > first

    def test_no_eta_on_the_very_first_batch(self):
        """Nothing to extrapolate from yet; a guess would be a lie."""
        stream = io.StringIO()
        reporter = ConsoleProgressReporter(stream=stream)
        reporter.on_fold_begin(FOLD)

        reporter.on_batch_end(FOLD, 0, 468, {"loss": 0.5})

        assert "eta" not in stream.getvalue()


class TestEveryEpochIsCheckpointed:
    def test_the_trainer_accepts_a_per_epoch_hook(self):
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

        trainer = WavenetTrainer(series=[[0.0, 0.0]], target_column=1, window_size=2)

        assert hasattr(trainer, "on_epoch_model")
        assert trainer.on_epoch_model is None  # off unless the caller asks

    def test_the_service_forwards_the_hook(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / "src/ShadBotTrader/application/services/dual_model_service.py"
        ).read_text(encoding="utf-8")

        assert "on_epoch_model" in source
        assert "trainer.on_epoch_model = on_epoch_model" in source

    def test_the_script_builds_a_checkpoint_callback(self):
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py").read_text(
            encoding="utf-8"
        )

        assert "make_epoch_checkpoint" in source
        assert "on_epoch_model=checkpoint" in source

    def test_a_checkpoint_writes_an_artifact_and_a_record(self, tmp_path):
        """The rescue copy must be a real, loadable model."""
        pytest.importorskip("tensorflow")
        import importlib.util
        from pathlib import Path

        import tensorflow as tf

        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
        spec = importlib.util.spec_from_file_location("rdm_ckpt", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Args:
            storage_root = str(tmp_path)
            symbol = "TESTSYM"
            folds = 1

        class Role:
            model_id = "gold_range_1d"
            name = "range"
            window_size = 32
            horizon = 5

        class Dataset:
            series = [[0.0] * 10 for _ in range(500)]
            feature_count = 8

        checkpoint = module.make_epoch_checkpoint(Args(), Role(), "1D", Dataset())

        model = tf.keras.Sequential([tf.keras.layers.Dense(2, input_shape=(4,))])
        checkpoint(model, 7, {"loss": 0.044, "val_mae": 0.0006}, 20)

        record = ModelCatalogue(tmp_path).read("gold_range_1d", 1)
        assert record is not None
        assert record.epochs == 8  # 1-based for humans
        assert "checkpoint after epoch 8/20" in record.note
        assert (tmp_path / "models/gold_range_1d/v1.bin").exists()

    def test_a_later_checkpoint_replaces_the_earlier_one(self, tmp_path):
        """One rescue copy, not twenty — this is a lifeline, not history."""
        pytest.importorskip("tensorflow")
        import importlib.util
        from pathlib import Path

        import tensorflow as tf

        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
        spec = importlib.util.spec_from_file_location("rdm_ckpt2", script)
        assert spec and spec.loader
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        class Args:
            storage_root = str(tmp_path)
            symbol = "TESTSYM"
            folds = 1

        class Role:
            model_id = "gold_range_1d"
            name = "range"
            window_size = 32
            horizon = 5

        class Dataset:
            series = [[0.0] * 10 for _ in range(500)]
            feature_count = 8

        checkpoint = module.make_epoch_checkpoint(Args(), Role(), "1D", Dataset())
        model = tf.keras.Sequential([tf.keras.layers.Dense(2, input_shape=(4,))])

        checkpoint(model, 0, {"loss": 0.9}, 20)
        checkpoint(model, 1, {"loss": 0.8}, 20)

        versions = sorted((tmp_path / "models/gold_range_1d").glob("v*.bin"))
        assert len(versions) == 1

        record = ModelCatalogue(tmp_path).read("gold_range_1d", 1)
        assert record is not None and record.epochs == 2

    def test_a_failing_checkpoint_never_aborts_training(self):
        """Losing a rescue copy is bad; losing the run is worse."""
        pytest.importorskip("tensorflow")
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
            _EpochCheckpoint,
        )

        def explode(*args, **kwargs):
            raise OSError("disk full")

        callback = _EpochCheckpoint(explode, object(), 20)
        callback.set_model(object())

        callback.on_epoch_end(0, {"loss": 0.5})  # must not raise


class TestTheTimeoutIsGenerousAndVisible:
    @pytest.mark.parametrize("kind", [CommandKind.TRAIN_DUAL_MODELS, CommandKind.TRAIN_MODEL])
    def test_the_operator_can_set_the_limit(self, kind, tmp_path):
        descriptor = next(item for item in descriptors(tmp_path) if item.kind is kind)
        field = next(item for item in descriptor.fields if item.name == "timeout_minutes")

        assert field.kind == "number"
        assert int(field.default) >= 240, "two hours was not enough for real data"

    def test_the_timeout_message_says_the_work_survived(self):
        from pathlib import Path

        source = (
            Path(__file__).resolve().parents[2]
            / "src/ShadBotTrader/presentation/commands/handlers.py"
        ).read_text(encoding="utf-8")

        assert "checkpointed" in source
