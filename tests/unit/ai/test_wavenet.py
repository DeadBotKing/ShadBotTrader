"""Tests for the WaveNet model (TensorFlow) and roll-forward training.

TensorFlow is a heavy optional dependency, so these tests are skipped by
default. Run them explicitly on a machine with TensorFlow::

    RUN_TF=1 python -m pytest tests/unit/ai/test_wavenet.py
"""

import os

import numpy as np
import pytest

pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_TF") != "1",
    reason="TensorFlow tests are skipped by default (set RUN_TF=1 to enable)",
)


def _tf():
    """Import TensorFlow lazily (heavy dependency)."""
    import tensorflow as tf

    return tf


def _definition():
    from ShadBotTrader.domain.ai.model_definition import ModelDefinition
    from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
    from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType

    return ModelDefinition(
        model_id=ModelId("gold_direction"),
        version=ModelVersion(1),
        name="Gold direction",
        model_type=ModelType.CLASSIFICATION,
        family=ModelFamily.WAVENET,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        target_name="direction",
        hyperparameters={"window_size": 4, "learning_rate": 1e-3},
    )


def _run():
    from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
    from ShadBotTrader.domain.ai.training_run import TrainingRun

    return TrainingRun(
        run_id="r1",
        model_id=ModelId("gold_direction"),
        model_version=ModelVersion(1),
        dataset_version=1,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        seed=42,
    )


def _series(n: int = 30) -> list[list[float]]:
    rng = np.random.default_rng(42)
    rows = []
    for _ in range(n):
        rows.append(
            [
                rng.normal(0, 0.01),
                rng.uniform(0, 0.02),
                rng.normal(0, 0.005),
                rng.uniform(0, 5),
                float(rng.integers(0, 2)),
            ]
        )
    return rows


def test_build_wavenet_shapes():
    _tf()
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import build_wavenet

    model = build_wavenet(
        window_size=4,
        n_features=4,
        output_units=2,
        n_filters=4,
        n_layers_per_block=1,
        n_blocks=1,
        depth_multiplier=1,
    )
    assert model.input_shape == (None, 4, 4)
    assert model.output_shape == (None, 2)


def test_wavenet_trainer_roll_forward_produces_artifact():
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

    trainer = WavenetTrainer(
        series=_series(),
        target_column=4,
        window_size=4,
        val_size=2,
        step=2,
        min_train_size=6,
        epochs=1,
        batch_size=4,
        output_units=2,
        seed=42,
        verbose=0,
        n_filters=4,
        kernel_size=3,
        n_layers_per_block=1,
        n_blocks=1,
        depth_multiplier=1,
    )
    artifact = trainer.train(_definition(), _run())
    assert artifact.framework == "tensorflow"
    assert len(artifact.checksum) == 64
    assert len(trainer.fold_history) >= 1
    assert artifact.payload


def test_wavenet_predictor_runs():
    from ShadBotTrader.domain.ai.inference import InferenceRequest
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
        WavenetPredictor,
        WavenetTrainer,
    )

    series = _series()
    trainer = WavenetTrainer(
        series=series,
        target_column=4,
        window_size=4,
        val_size=2,
        step=2,
        min_train_size=6,
        epochs=1,
        batch_size=4,
        output_units=2,
        seed=42,
        verbose=0,
        n_filters=4,
        kernel_size=3,
        n_layers_per_block=1,
        n_blocks=1,
        depth_multiplier=1,
    )
    artifact = trainer.train(_definition(), _run())

    predictor = WavenetPredictor()
    request = InferenceRequest(
        model_id="gold_direction",
        model_version=1,
        features=[row[:-1] for row in series[-4:]],
        feature_names=["return_1", "range_pct", "body_pct", "volume_log"],
    )
    prediction = predictor.predict(_definition(), artifact, request)
    assert prediction.confidence.value > 0.0
    assert prediction.value in (0.0, 1.0)


def test_wavenet_model_survives_save_load_roundtrip():
    """Regression guard: the gated-activation layer must be deserializable.

    The custom layer used to be declared inside a factory function, so
    Keras could not resolve the class when loading a saved model and
    ``load_model`` raised "Could not locate class '_GatedActivationUnit'".
    """
    import numpy as np

    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import build_wavenet
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
        _deserialize_model,
        _serialize_model,
    )

    model = build_wavenet(
        window_size=4,
        n_features=3,
        n_filters=4,
        kernel_size=3,
        n_layers_per_block=1,
        n_blocks=1,
        depth_multiplier=1,
    )
    payload = _serialize_model(model)
    restored = _deserialize_model(payload)

    x = np.random.default_rng(0).normal(size=(2, 4, 3)).astype("float32")
    np.testing.assert_allclose(
        model.predict(x, verbose=0), restored.predict(x, verbose=0), rtol=1e-5
    )


def test_wavenet_predictor_rejects_wrong_feature_count():
    """The predictor must reject a window whose width does not match the model."""
    from ShadBotTrader.domain.ai.inference import InferenceRequest
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
        WavenetPredictor,
        WavenetTrainer,
    )

    series = _series()
    trainer = WavenetTrainer(
        series=series,
        target_column=4,
        window_size=4,
        val_size=2,
        step=2,
        min_train_size=6,
        epochs=1,
        batch_size=4,
        output_units=2,
        seed=42,
        verbose=0,
        n_filters=4,
        kernel_size=3,
        n_layers_per_block=1,
        n_blocks=1,
        depth_multiplier=1,
    )
    artifact = trainer.train(_definition(), _run())

    # passing the full row (target column included) is one column too wide
    bad = InferenceRequest(
        model_id="gold_direction",
        model_version=1,
        features=[list(row) for row in series[-4:]],
        feature_names=[],
    )
    with pytest.raises(ValueError, match="features but the model expects"):
        WavenetPredictor().predict(_definition(), artifact, bad)


def test_wavenet_trainer_reports_progress_and_respects_max_folds():
    """The trainer must drive the progress contract and honour --folds."""
    from ShadBotTrader.infrastructure.ai.training_progress import (
        EpochMetrics,
        FoldInfo,
        TrainingPlanInfo,
    )
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

    class RecordingReporter:
        def __init__(self) -> None:
            self.plan = None
            self.folds: list[FoldInfo] = []
            self.epochs: list[EpochMetrics] = []
            self.fold_losses: list[float] = []
            self.finished: list[float] | None = None

        def on_train_begin(self, plan: TrainingPlanInfo) -> None:
            self.plan = plan

        def on_fold_begin(self, fold: FoldInfo) -> None:
            self.folds.append(fold)

        def on_epoch_end(self, fold: FoldInfo, metrics: EpochMetrics) -> None:
            self.epochs.append(metrics)

        def on_fold_end(self, fold: FoldInfo, val_loss: float) -> None:
            self.fold_losses.append(val_loss)

        def on_train_end(self, fold_losses: list[float]) -> None:
            self.finished = fold_losses

    reporter = RecordingReporter()
    trainer = WavenetTrainer(
        series=_series(40),
        target_column=4,
        window_size=4,
        val_size=2,
        step=2,
        min_train_size=6,
        epochs=2,
        batch_size=4,
        output_units=2,
        seed=42,
        verbose=0,
        n_filters=4,
        kernel_size=3,
        n_layers_per_block=1,
        n_blocks=1,
        depth_multiplier=1,
        progress=reporter,
        max_folds=2,
    )
    trainer.train(_definition(), _run())

    # max_folds caps the work
    assert len(trainer.fold_history) == 2
    assert len(reporter.folds) == 2
    assert reporter.fold_losses == trainer.fold_history
    assert reporter.finished == trainer.fold_history

    # the plan describes the run accurately
    assert reporter.plan is not None
    assert reporter.plan.total_folds == 2
    assert reporter.plan.epochs_per_fold == 2
    assert reporter.plan.learning_rate == 1e-3
    assert reporter.plan.n_features == 4  # target column excluded

    # epoch metrics arrive for every epoch of every fold
    assert len(reporter.epochs) == 4
    assert all(metric.loss is not None for metric in reporter.epochs)
    assert all(metric.val_loss is not None for metric in reporter.epochs)

    # folds are numbered 1..N for display
    assert [fold.human_index for fold in reporter.folds] == [1, 2]
