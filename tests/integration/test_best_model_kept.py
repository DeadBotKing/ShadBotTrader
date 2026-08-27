"""Phase 47 — the BEST epoch is kept, not the last one.

The operator asked: "do the trained models save the last model, or the
best one they reached?" The honest answer was: the last one.

    last_model = model          # every fold, unconditionally
    payload = _serialize_model(last_model)

Training loss falls almost monotonically. Validation loss does not: it
falls, bottoms out, then climbs as the network memorises. Saving
whatever ran last therefore saves the most overfitted weights of the
run. Measured on real synthetic data:

    epoch  5 | val_loss 0.8055 | val_acc 72.7%   <- best
    epoch 12 | val_loss 0.8969 | val_acc 63.6%   <- what used to be saved

Nine accuracy points, thrown away by a variable assignment.
"""

import pytest


def load_script():
    import importlib.util
    from pathlib import Path

    script = Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py"
    spec = importlib.util.spec_from_file_location("rdm_best", script)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Args:
    def __init__(self, root):
        self.storage_root = str(root)
        self.symbol = "TESTSYM"
        self.folds = 1


class Target:
    """Phase 49: the real ModelRole carries the label rule on `target`.

    The stub grew it too, because the checkpoint now records the neutral
    band with the model. A stub that lags the real object hides exactly
    the kind of AttributeError this file exists to catch.
    """

    threshold = 0.0008


class Role:
    model_id = "gold_signal_5m"
    name = "signal"
    window_size = 32
    horizon = 5
    target = Target()
    # فاز ۷۰: اسکریپت role.loss را در ModelRecord می‌نویسد — mock هم باید
    # داشته باشد (قبل از نصب TF این تست‌ها skip می‌شدند و دیده نمی‌شد).
    loss = "sparse_categorical_crossentropy"
    metric = "accuracy"


class Dataset:
    series = [[0.0] * 10 for _ in range(500)]
    feature_count = 8


@pytest.fixture
def checkpoint(tmp_path):
    pytest.importorskip("tensorflow")
    module = load_script()
    return module.make_epoch_checkpoint(Args(tmp_path), Role(), "5M", Dataset())


def a_model():
    import tensorflow as tf

    return tf.keras.Sequential([tf.keras.layers.Dense(3, input_shape=(4,))])


class TestOnlyImprovementsAreWritten:
    def test_a_worse_epoch_does_not_overwrite_the_best(self, checkpoint, tmp_path):
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        model = a_model()
        checkpoint(model, 0, {"val_loss": 0.90}, 10)  # first: always saved
        checkpoint(model, 1, {"val_loss": 0.80}, 10)  # better: saved
        checkpoint(model, 2, {"val_loss": 0.95}, 10)  # worse: ignored
        checkpoint(model, 3, {"val_loss": 1.20}, 10)  # worse: ignored

        record = ModelCatalogue(tmp_path).read("gold_signal_5m", 1)

        assert record is not None
        assert record.epochs == 2, "the best epoch was 2, not the last one"
        assert record.metrics["val_loss"] == pytest.approx(0.80)

    def test_the_classic_overfit_curve_keeps_the_bottom(self, checkpoint, tmp_path):
        """Down, bottom, then up — the shape every real run has."""
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        model = a_model()
        curve = [0.71, 0.55, 0.51, 0.53, 0.58, 0.64]
        for index, val_loss in enumerate(curve):
            checkpoint(model, index, {"val_loss": val_loss}, len(curve))

        record = ModelCatalogue(tmp_path).read("gold_signal_5m", 1)

        assert record is not None
        assert record.epochs == 3  # the 0.51 epoch, 1-based
        assert record.metrics["val_loss"] == pytest.approx(0.51)

    def test_a_monotonically_improving_run_keeps_the_last(self, checkpoint, tmp_path):
        """When nothing overfits, last IS best — the operator's own run."""
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        model = a_model()
        for index, val_loss in enumerate([0.60, 0.55, 0.53, 0.52]):
            checkpoint(model, index, {"val_loss": val_loss}, 4)

        record = ModelCatalogue(tmp_path).read("gold_signal_5m", 1)

        assert record is not None
        assert record.epochs == 4

    def test_only_one_version_survives(self, checkpoint, tmp_path):
        """A rescue copy, not a museum of every epoch."""
        model = a_model()
        for index, val_loss in enumerate([0.9, 0.8, 0.7, 0.6]):
            checkpoint(model, index, {"val_loss": val_loss}, 4)

        artifacts = sorted((tmp_path / "models/gold_signal_5m").glob("v*.bin"))

        assert len(artifacts) == 1

    def test_the_note_names_the_epoch_that_won(self, checkpoint, tmp_path):
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        model = a_model()
        checkpoint(model, 0, {"val_loss": 0.9}, 20)
        checkpoint(model, 6, {"val_loss": 0.4}, 20)

        record = ModelCatalogue(tmp_path).read("gold_signal_5m", 1)

        assert record is not None
        assert "best epoch 7/20" in record.note

    def test_a_range_model_falls_back_to_val_mae(self, tmp_path):
        """Regression models report mae, not accuracy."""
        pytest.importorskip("tensorflow")
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        module = load_script()

        class RangeRole(Role):
            model_id = "gold_range_1d"
            name = "range"

        checkpoint = module.make_epoch_checkpoint(Args(tmp_path), RangeRole(), "1D", Dataset())
        model = a_model()
        checkpoint(model, 0, {"val_mae": 0.02}, 5)
        checkpoint(model, 1, {"val_mae": 0.05}, 5)  # worse
        checkpoint(model, 2, {"val_mae": 0.01}, 5)  # best

        record = ModelCatalogue(tmp_path).read("gold_range_1d", 1)

        assert record is not None
        assert record.epochs == 3


class TestTheFinalSaveDoesNotUndoIt:
    def test_a_worse_final_epoch_is_refused(self, tmp_path, capsys):
        """The last epoch's weights must not become a second version."""
        pytest.importorskip("tensorflow")
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        module = load_script()
        args = Args(tmp_path)
        checkpoint = module.make_epoch_checkpoint(args, Role(), "5M", Dataset())

        model = a_model()
        checkpoint(model, 4, {"val_loss": 0.80}, 12)  # best, epoch 5

        outcome = {
            "artifact": None,
            "fold_metrics": [{"val_loss": 0.90}],  # last epoch, worse
        }
        module.save_model(outcome, args, Role(), "5M", Dataset(), checkpoint)

        printed = capsys.readouterr().out
        assert "KEPT" in printed
        assert "epoch 5" in printed
        assert len(sorted((tmp_path / "models/gold_signal_5m").glob("v*.bin"))) == 1

        record = ModelCatalogue(tmp_path).read("gold_signal_5m", 1)
        assert record is not None and record.epochs == 5

    def test_the_source_no_longer_blindly_serialises_the_last_model(self):
        """A guard against the old one-line behaviour returning."""
        from pathlib import Path

        source = (Path(__file__).resolve().parents[2] / "scripts" / "run_dual_models.py").read_text(
            encoding="utf-8"
        )

        assert "best_score" in source
        assert "best_epoch" in source


class TestBothRolesBehaveIdentically:
    """The operator asked whether BOTH models keep their best epoch.

    They share ``train_one``, so structurally the answer is yes — but
    "it should work" is not evidence. Each role is driven through the
    same overfit curve, expressed in the metric that role actually
    reports, and the saved epoch is checked.
    """

    CURVES = [
        # (model_id, role, timeframe, metric, curve, expected best epoch)
        ("gold_signal_5m", "signal", "5M", "val_loss", [0.71, 0.55, 0.51, 0.53, 0.58, 0.64], 3),
        ("gold_range_1d", "range", "1D", "val_mae", [0.031, 0.022, 0.018, 0.021, 0.027, 0.034], 3),
    ]

    @pytest.mark.parametrize("model_id,role_name,timeframe,metric,curve,best_epoch", CURVES)
    def test_the_bottom_of_the_curve_is_kept(
        self, tmp_path, model_id, role_name, timeframe, metric, curve, best_epoch
    ):
        pytest.importorskip("tensorflow")
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        module = load_script()

        class ThisRole(Role):
            pass

        ThisRole.model_id = model_id
        ThisRole.name = role_name

        checkpoint = module.make_epoch_checkpoint(Args(tmp_path), ThisRole(), timeframe, Dataset())
        model = a_model()
        for index, value in enumerate(curve):
            checkpoint(model, index, {metric: value}, len(curve))

        record = ModelCatalogue(tmp_path).read(model_id, 1)

        assert record is not None
        assert record.epochs == best_epoch
        assert record.role == role_name
        assert len(sorted((tmp_path / "models" / model_id).glob("v*.bin"))) == 1

    @pytest.mark.parametrize("model_id,role_name,timeframe,metric,curve,best_epoch", CURVES)
    def test_the_note_names_the_metric_that_was_judged(
        self, tmp_path, model_id, role_name, timeframe, metric, curve, best_epoch
    ):
        """A range model printing "val_loss" would send the operator
        hunting for a number that does not exist in its logs."""
        pytest.importorskip("tensorflow")
        from ShadBotTrader.infrastructure.ai.model_catalogue import ModelCatalogue

        module = load_script()

        class ThisRole(Role):
            pass

        ThisRole.model_id = model_id
        ThisRole.name = role_name

        checkpoint = module.make_epoch_checkpoint(Args(tmp_path), ThisRole(), timeframe, Dataset())
        model = a_model()
        for index, value in enumerate(curve):
            checkpoint(model, index, {metric: value}, len(curve))

        record = ModelCatalogue(tmp_path).read(model_id, 1)

        assert record is not None
        assert metric in record.note
