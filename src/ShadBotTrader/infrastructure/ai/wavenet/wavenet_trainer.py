"""WaveNet trainer with genuine roll-forward (walk-forward) training.

Each fold trains a fresh model on a rolling training window and
validates on the window that immediately follows it; the model from the
final fold (trained on the most recent data) becomes the artifact. This
is the canonical time-series methodology — no future data ever leaks
into a training window (Phase 13, sections 32, 46-47).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import List, Sequence

from ShadBotTrader.domain.ai.inference import InferenceRequest
from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_types import PredictionType
from ShadBotTrader.domain.ai.ports import ModelPredictor, ModelTrainer
from ShadBotTrader.domain.ai.prediction import Confidence, Prediction
from ShadBotTrader.domain.ai.training_run import TrainingRun
from ShadBotTrader.infrastructure.ai.data_windowing import build_samples
from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split


def _serialize_model(model) -> bytes:
    """Serialize a Keras model to bytes via a temporary .keras file."""

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "model.keras"
        model.save(path)
        return path.read_bytes()


def _deserialize_model(payload: bytes):
    """Load a Keras model from bytes."""
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import _require_tensorflow

    tf = _require_tensorflow()

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "model.keras"
        path.write_bytes(payload)
        return tf.keras.models.load_model(path)


class WavenetTrainer(ModelTrainer):
    """Trains a WaveNet model with roll-forward (walk-forward) training.

    The trainer is constructed with the full feature series; ``train``
    performs walk-forward training and returns the final model as an
    immutable artifact. Fold validation losses are exposed via
    ``fold_history`` for reproducibility reporting.
    """

    def __init__(
        self,
        series: Sequence[Sequence[float]],
        target_column: int,
        window_size: int,
        val_size: int = 4,
        step: int = 2,
        min_train_size: int = 8,
        epochs: int = 2,
        batch_size: int = 8,
        output_units: int = 2,
        output_activation: str = "sigmoid",
        seed: int = 42,
        verbose: int = 0,
        n_filters: int = 32,
        kernel_size: int = 5,
        n_layers_per_block: int = 4,
        n_blocks: int = 2,
        depth_multiplier: int = 20,
    ) -> None:
        self._series = [list(row) for row in series]
        self._target_column = target_column
        self._window_size = window_size
        self._val_size = val_size
        self._step = step
        self._min_train_size = min_train_size
        self._epochs = epochs
        self._batch_size = batch_size
        self._output_units = output_units
        self._output_activation = output_activation
        self._seed = seed
        self._verbose = verbose
        self._n_filters = n_filters
        self._kernel_size = kernel_size
        self._n_layers_per_block = n_layers_per_block
        self._n_blocks = n_blocks
        self._depth_multiplier = depth_multiplier
        self.fold_history: List[float] = []

    @property
    def framework(self) -> str:
        return "tensorflow"

    def train(self, definition: ModelDefinition, run: TrainingRun) -> ModelArtifact:
        import numpy as np

        from ShadBotTrader.infrastructure.ai.wavenet.wavenet import _require_tensorflow

        tf = _require_tensorflow()
        tf.random.set_seed(self._seed)
        np.random.seed(self._seed)

        samples = build_samples(
            self._series,
            window_size=self._window_size,
            target_column=self._target_column,
            scale=True,
        )
        plan = expanding_split(
            total_length=len(samples),
            val_size=self._val_size,
            step=self._step,
            min_train_size=self._min_train_size,
        )

        self.fold_history = []
        last_model = None
        n_features = len(self._series[0])

        for fold in plan.folds:
            train_x, train_y = self._arrays(samples[fold.train_start : fold.train_end])
            val_x, val_y = self._arrays(samples[fold.val_start : fold.val_end])

            model = _build_compiled(
                window_size=self._window_size,
                n_features=n_features,
                output_units=self._output_units,
                output_activation=self._output_activation,
                learning_rate=float(definition.hyperparameters.get("learning_rate", 1.5e-4)),
                seed=self._seed,
                n_filters=self._n_filters,
                kernel_size=self._kernel_size,
                n_layers_per_block=self._n_layers_per_block,
                n_blocks=self._n_blocks,
                depth_multiplier=self._depth_multiplier,
            )

            history = model.fit(
                train_x,
                train_y,
                validation_data=(val_x, val_y),
                epochs=self._epochs,
                batch_size=self._batch_size,
                verbose=self._verbose,
            )
            val_loss = float(history.history["val_loss"][-1])
            self.fold_history.append(val_loss)
            last_model = model

        if last_model is None:
            raise RuntimeError(
                f"Roll-forward produced no training folds "
                f"(series too short: {len(samples)} samples)"
            )

        payload = _serialize_model(last_model)
        return ModelArtifact.create(
            model_id=definition.model_id,
            version=definition.version,
            framework=self.framework,
            framework_version=self._tf_version(),
            format="keras",
            payload=payload,
            training_run_id=run.run_id,
        )

    def _arrays(self, samples) -> tuple:
        import numpy as np

        x = np.array([sample.features for sample in samples], dtype=np.float32)
        y = np.array(
            [int(sample.target) if sample.target is not None else 0 for sample in samples],
            dtype=np.int32,
        )
        return x, y

    @staticmethod
    def _tf_version() -> str:
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet import _require_tensorflow

        return _require_tensorflow().__version__


def _build_compiled(
    window_size: int,
    n_features: int,
    output_units: int,
    output_activation: str,
    learning_rate: float,
    seed: int,
    n_filters: int = 32,
    kernel_size: int = 5,
    n_layers_per_block: int = 4,
    n_blocks: int = 2,
    depth_multiplier: int = 20,
):
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import (
        _require_tensorflow,
        build_wavenet,
    )

    tf = _require_tensorflow()

    model = build_wavenet(
        window_size=window_size,
        n_features=n_features,
        n_filters=n_filters,
        kernel_size=kernel_size,
        n_layers_per_block=n_layers_per_block,
        n_blocks=n_blocks,
        output_units=output_units,
        output_activation=output_activation,
        depth_multiplier=depth_multiplier,
    )
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")],
    )
    return model


class WavenetPredictor(ModelPredictor):
    """Runs inference with a trained WaveNet artifact."""

    def predict(
        self,
        definition: ModelDefinition,
        artifact: ModelArtifact,
        request: InferenceRequest,
    ) -> Prediction:
        import numpy as np

        from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window

        model = _deserialize_model(artifact.payload)
        window = request.features
        if not window:
            raise ValueError("InferenceRequest has no features")
        scaled = minmax_scale_window(window)
        x = np.array([scaled[0]], dtype=np.float32)
        probabilities = model.predict(x, verbose=0)[0]
        predicted_class = int(np.argmax(probabilities))
        confidence = float(probabilities[predicted_class])

        return Prediction(
            model_id=definition.model_id.value,
            model_version=definition.version.number,
            prediction_type=PredictionType.CLASS_LABEL,
            value=float(predicted_class),
            confidence=Confidence(confidence),
            horizon=1,
        )
