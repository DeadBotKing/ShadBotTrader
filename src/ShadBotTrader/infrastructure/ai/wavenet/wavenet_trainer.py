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
from ShadBotTrader.infrastructure.ai.data_windowing import (
    build_multi_target_samples,
    build_samples,
)
from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split
from ShadBotTrader.infrastructure.ai.training_progress import (
    FoldInfo,
    NullProgressReporter,
    TrainingPlanInfo,
    TrainingProgressReporter,
    keras_progress_callback,
)


def _serialize_model(model) -> bytes:
    """Serialize a Keras model to bytes via a temporary .keras file."""

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "model.keras"
        model.save(path)
        return path.read_bytes()


def _deserialize_model(payload: bytes):
    """Load a Keras model from bytes.

    The WaveNet uses a custom gated-activation layer, so the custom
    objects must be supplied for deserialization to resolve the class.
    """
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import (
        _require_tensorflow,
        custom_objects,
    )

    tf = _require_tensorflow()

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "model.keras"
        path.write_bytes(payload)
        return tf.keras.models.load_model(path, custom_objects=custom_objects())


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
        progress: TrainingProgressReporter | None = None,
        max_folds: int | None = None,
        target_columns: Sequence[int] | None = None,
        loss: str | None = None,
        metric: str | None = None,
    ) -> None:
        """Train a WaveNet with roll-forward validation.

        Args:
            target_columns: for the Phase 29 **regression** head, the
                indices of the continuous target columns (e.g. future
                high and low offsets). When given, the trainer switches
                to a multi-output float target and ``target_column`` is
                ignored. Leave as None for the original single-label
                classification behaviour.
            loss: overrides the loss function. Defaults to sparse
                categorical cross-entropy for classification and MSE for
                regression.
            metric: overrides the reported metric.
        """
        self._series = [list(row) for row in series]
        self._target_column = target_column
        self._target_columns = list(target_columns) if target_columns is not None else None
        self._loss = loss
        self._metric = metric
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
        self._progress: TrainingProgressReporter = progress or NullProgressReporter()
        self._max_folds = max_folds
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

        if self._target_columns is not None:
            samples = build_multi_target_samples(
                self._series,
                window_size=self._window_size,
                target_columns=self._target_columns,
                scale=True,
            )
        else:
            samples = build_samples(
                self._series,
                window_size=self._window_size,
                target_column=self._target_column,
                scale=True,
                drop_target_column=True,
            )
        plan = expanding_split(
            total_length=len(samples),
            val_size=self._val_size,
            step=self._step,
            min_train_size=self._min_train_size,
        )

        folds = plan.folds
        if self._max_folds is not None and self._max_folds > 0:
            # Keep the LAST folds: they train on the most recent data, and
            # the final fold's model is the one promoted to the artifact.
            folds = folds[-self._max_folds :]

        self.fold_history = []
        last_model = None
        # Target columns are removed from the feature windows, so the
        # model sees fewer columns than the raw series has.
        dropped = len(self._target_columns) if self._target_columns is not None else 1
        n_features = len(self._series[0]) - dropped
        learning_rate = float(definition.hyperparameters.get("learning_rate", 1.5e-4))
        total_folds = len(folds)

        self._progress.on_train_begin(
            TrainingPlanInfo(
                model_id=definition.model_id.value,
                model_version=definition.version.number,
                total_folds=total_folds,
                epochs_per_fold=self._epochs,
                learning_rate=learning_rate,
                batch_size=self._batch_size,
                window_size=self._window_size,
                n_features=n_features,
                total_samples=len(samples),
                seed=self._seed,
                framework=self.framework,
                framework_version=self._tf_version(),
            )
        )

        for display_index, fold in enumerate(folds):
            train_x, train_y = self._arrays(samples[fold.train_start : fold.train_end])
            val_x, val_y = self._arrays(samples[fold.val_start : fold.val_end])

            fold_info = FoldInfo(
                fold_index=display_index,
                total_folds=total_folds,
                train_samples=len(train_x),
                val_samples=len(val_x),
                train_start=fold.train_start,
                train_end=fold.train_end,
                val_start=fold.val_start,
                val_end=fold.val_end,
            )
            self._progress.on_fold_begin(fold_info)

            model = _build_compiled(
                window_size=self._window_size,
                n_features=n_features,
                output_units=self._output_units,
                output_activation=self._output_activation,
                learning_rate=learning_rate,
                seed=self._seed,
                n_filters=self._n_filters,
                kernel_size=self._kernel_size,
                n_layers_per_block=self._n_layers_per_block,
                n_blocks=self._n_blocks,
                depth_multiplier=self._depth_multiplier,
                loss=self._loss,
                metric=self._metric,
            )

            callbacks = []
            if not isinstance(self._progress, NullProgressReporter):
                callbacks.append(keras_progress_callback(self._progress, fold_info, self._epochs))

            history = model.fit(
                train_x,
                train_y,
                validation_data=(val_x, val_y),
                epochs=self._epochs,
                batch_size=self._batch_size,
                verbose=self._verbose,
                callbacks=callbacks,
            )
            val_loss = float(history.history["val_loss"][-1])
            self.fold_history.append(val_loss)
            last_model = model
            self._progress.on_fold_end(fold_info, val_loss)

        self._progress.on_train_end(list(self.fold_history))

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

        if self._target_columns is not None:
            # Regression: several continuous targets per row, kept as
            # float. Casting these to int (the classification path) would
            # collapse every offset to zero.
            y = np.array(
                [
                    [float(value) if value is not None else 0.0 for value in (sample.targets or [])]
                    for sample in samples
                ],
                dtype=np.float32,
            )
            return x, y

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
    loss: str | None = None,
    metric: str | None = None,
):
    """Build and compile the network for the requested task.

    The loss defaults to sparse categorical cross-entropy so the original
    direction model is unaffected. Phase 29's range model passes
    ``loss="mse"`` with a linear head, which is the combination a
    classification-only compile step made impossible.
    """
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import (
        _require_tensorflow,
        build_wavenet,
    )

    tf = _require_tensorflow()

    # Reproducibility (Phase 13 §34). ``tf.random.set_seed`` alone is not
    # enough in Keras 3: each layer draws its initial weights from its own
    # generator, so a fresh model built later in the same process starts
    # from different weights. ``keras.utils.set_random_seed`` re-seeds
    # Python, NumPy and the backend together, which is what makes two runs
    # of the same configuration actually produce the same model.
    try:
        import keras as _keras  # type: ignore[import-not-found]

        _keras.utils.set_random_seed(seed)
    except (ImportError, AttributeError):  # pragma: no cover - legacy TF
        tf.keras.utils.set_random_seed(seed)

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

    if loss in ("mse", "mean_squared_error"):
        compiled_loss: object = tf.keras.losses.MeanSquaredError()
        compiled_metrics = [tf.keras.metrics.MeanAbsoluteError(name=metric or "mae")]
    elif loss in ("mae", "mean_absolute_error"):
        compiled_loss = tf.keras.losses.MeanAbsoluteError()
        compiled_metrics = [tf.keras.metrics.MeanSquaredError(name=metric or "mse")]
    else:
        compiled_loss = tf.keras.losses.SparseCategoricalCrossentropy()
        compiled_metrics = [tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")]

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss=compiled_loss,
        metrics=compiled_metrics,
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
        # The model consumes a full (window_size, n_features) window, so
        # the batch axis wraps the whole window - not just its first row.
        x = np.array([scaled], dtype=np.float32)

        expected = model.input_shape  # (None, window_size, n_features)
        if len(expected) == 3:
            exp_window, exp_features = expected[1], expected[2]
            if exp_window is not None and x.shape[1] != exp_window:
                raise ValueError(
                    f"InferenceRequest window has {x.shape[1]} time steps but the "
                    f"model expects {exp_window}."
                )
            if exp_features is not None and x.shape[2] != exp_features:
                raise ValueError(
                    f"InferenceRequest window has {x.shape[2]} features but the "
                    f"model expects {exp_features}. The target column must be "
                    f"excluded from inference features."
                )

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
