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
from typing import Any, Dict, List, Sequence

from ShadBotTrader.domain.ai.inference import InferenceRequest
from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_types import PredictionType
from ShadBotTrader.domain.ai.ports import ModelPredictor, ModelTrainer
from ShadBotTrader.domain.ai.prediction import Confidence, Prediction
from ShadBotTrader.domain.ai.training_run import TrainingRun
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.ai.data_windowing import (
    build_multi_target_samples,
    build_samples,
    build_samples_at,
)
from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split
from ShadBotTrader.infrastructure.ai.training_progress import (
    FoldInfo,
    NullProgressReporter,
    TrainingPlanInfo,
    TrainingProgressReporter,
    keras_batch_callback,
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
        depth_multiplier: int = 8,
        l2: float = 2.5e-4,
        dropout: float = 0.10,
        progress: TrainingProgressReporter | None = None,
        max_folds: int | None = None,
        target_columns: Sequence[int] | None = None,
        loss: str | None = None,
        metric: str | None = None,
        sample_indices: Sequence[int] | None = None,
        sample_label_ends: Sequence[int] | None = None,
        purge_gap: int = 0,
        initial_epoch: int = 0,
        resume_weights: bytes | None = None,
        seq2seq: bool = False,
        horizon: int = 5,
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
        self._sample_indices = list(sample_indices) if sample_indices is not None else None
        self._sample_label_ends = list(sample_label_ends) if sample_label_ends is not None else None
        if self._sample_indices is not None and self._sample_label_ends is not None:
            if len(self._sample_indices) != len(self._sample_label_ends):
                raise ValidationError("sample_label_ends must have one entry per sample")
        if purge_gap < 0:
            raise ValidationError("purge_gap must be >= 0")
        self._purge_gap = purge_gap
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
        self._l2 = float(l2)
        self._dropout = float(dropout)
        self._progress: TrainingProgressReporter = progress or NullProgressReporter()
        self._max_folds = max_folds
        self._initial_epoch = max(0, int(initial_epoch))
        self._resume_weights = resume_weights
        self._seq2seq = bool(seq2seq)
        self._horizon_s2s = max(1, int(horizon))
        #: Called as ``(model, epoch, logs)`` after each epoch so the
        #: caller can checkpoint. None disables checkpointing.
        self.on_epoch_model: Any = None
        self.fold_history: List[float] = []
        #: Lazily built window generator + the width it assumes (Phase 41).
        self._window_cache: Any = None
        self._samples: Any = []
        self._stream_all: bool = False
        self._n_features_cache: int = 0
        #: Final-epoch metrics per fold (loss, val_loss, accuracy, mae...).
        self.fold_metrics: List[Dict[str, float]] = []

    @property
    def framework(self) -> str:
        return "tensorflow"

    @property
    def _on_epoch_model(self) -> Any:
        return self.on_epoch_model

    def train(self, definition: ModelDefinition, run: TrainingRun) -> ModelArtifact:
        import numpy as np

        from ShadBotTrader.infrastructure.ai.wavenet.wavenet import _require_tensorflow

        tf = _require_tensorflow()
        tf.random.set_seed(self._seed)
        np.random.seed(self._seed)

        # Phase 39: building 50,000 overlapping windows takes ~10 seconds
        # and used to happen in total silence BEFORE on_train_begin, so
        # the first sign of life came long after the operator pressed the
        # button. Announce the preparation, then do it.
        _notify(self._progress, "on_prepare_begin", len(self._series), self._window_size)

        # Phase 41: decide BEFORE building anything. Materialising every
        # window is what exhausted the machine — 49,393 windows of
        # 500x123 float32 is 12.2 GB — and it happened here, at the top
        # of train(), before a single batch was fitted. When the windows
        # would be large the samples list is never built at all; the
        # folds stream straight from the 25 MB flat series instead.
        dropped_columns = len(self._target_columns) if self._target_columns is not None else 1
        feature_width = max(len(self._series[0]) - dropped_columns, 1)
        sample_count = (
            len(self._sample_indices)
            if self._sample_indices is not None
            else max(len(self._series) - self._window_size + 1, 0)
        )
        estimated_bytes = sample_count * self._window_size * feature_width * 4
        self._stream_all = estimated_bytes > self.STREAM_THRESHOLD_BYTES

        samples: Any
        if self._stream_all:
            samples = _LazySampleCount(sample_count)
        elif self._sample_indices is not None:
            samples = build_samples_at(
                self._series,
                window_size=self._window_size,
                target_column=self._target_column,
                sample_ends=self._sample_indices,
                scale=True,
                drop_target_column=True,
            )
        elif self._target_columns is not None:
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
        self._samples = samples
        _notify(self._progress, "on_prepare_end", len(samples))

        sample_end_indices = self._sample_indices
        if sample_end_indices is None:
            sample_end_indices = [self._window_size - 1 + index for index in range(len(samples))]
        if self._sample_label_ends is not None and len(self._sample_label_ends) != len(samples):
            raise ValidationError("sample_label_ends must have one entry per sample")
        plan = expanding_split(
            total_length=len(samples),
            val_size=self._val_size,
            step=self._step,
            min_train_size=self._min_train_size,
            purge_gap=self._purge_gap,
            sample_end_indices=(
                sample_end_indices if self._sample_label_ends is not None else None
            ),
            label_end_indices=self._sample_label_ends,
            window_size=self._window_size,
        )

        folds = plan.folds
        if self._max_folds is not None and self._max_folds > 0:
            # Keep the LAST folds: they train on the most recent data, and
            # the final fold's model is the one promoted to the artifact.
            folds = folds[-self._max_folds :]

        self.fold_history = []
        self.fold_metrics = []
        last_model = None
        # Target columns are removed from the feature windows, so the
        # model sees fewer columns than the raw series has.
        dropped = len(self._target_columns) if self._target_columns is not None else 1
        n_features = len(self._series[0]) - dropped
        self._n_features_cache = n_features
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
            # Phase 41: stream the windows instead of materialising them.
            # 49,393 windows of 500x123 float32 is 12.2 GB — the machine
            # runs out of RAM long before the first epoch ends, which is
            # exactly what the operator saw. tf.data pulls one batch at a
            # time from the same 25 MB flat matrix.
            train_size = fold.train_end - fold.train_start
            val_size = fold.val_end - fold.val_start
            train_x, train_y, train_steps = self._dataset_for(fold.train_start, fold.train_end)
            val_x, val_y, val_steps = self._dataset_for(fold.val_start, fold.val_end)

            fold_info = FoldInfo(
                fold_index=display_index,
                total_folds=total_folds,
                train_samples=train_size,
                val_samples=val_size,
                train_start=fold.train_start,
                train_end=fold.train_end,
                val_start=fold.val_start,
                val_end=fold.val_end,
                purged_train_samples=fold.purged_train_samples,
                validation_input_start=fold.validation_input_start,
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
                l2=getattr(self, "_l2", 2.5e-4),
                dropout=getattr(self, "_dropout", 0.10),
                seq2seq=self._seq2seq,
                horizon=self._horizon_s2s,
            )

            # Phase 50: resume — warm-start from a saved checkpoint.
            # Phase 57: resume — همه fold ها از checkpoint شروع میکنن
            # دلیل: کاربر میخواد از جایی که موند ادامه بده
            # هر fold با وزن‌های checkpoint warm-start میشه
            # این یعنی هر fold سریع‌تر converge میکنه
            is_last_fold = (display_index == len(folds) - 1)
            if self._resume_weights:
                _load_weights_into(model, self._resume_weights)

            callbacks = []
            if self._on_epoch_model is not None:
                # Phase 46: hand the live model out after every epoch so
                # a timeout cannot destroy hours of work. The operator
                # lost 18 completed epochs to the 2-hour limit because
                # nothing was persisted until train() returned.
                callbacks.append(_EpochCheckpoint(self._on_epoch_model, model, self._epochs))

            # Phase 54: ReduceLROnPlateau (ایده از legacy/TimeSeriesPrediction2.py)
            # LR ثابت در طول training ریسک گیر کردن در local minima داره.
            # ReduceLROnPlateau وقتی val_loss بهتر نشد LR رو کاهش میده.
            # فقط برای regression (range model) فعاله:
            #   factor=0.9: LR × 0.9 هر بار (ملایم، مثل legacy)
            #   patience=5: 5 epoch صبر میکنه (کوتاه‌تر از legacy=30 چون fold کوتاهه)
            #   min_lr: حداقل LR
            # ReduceLROnPlateau و EarlyStopping برای هر دو regression و classification
            if self._loss in ("huber", "huber_loss", "mse", "mean_squared_error",
                               "mae", "mean_absolute_error",
                               "sparse_categorical_crossentropy",
                               "categorical_crossentropy",
                               "focal"):
                _min_lr = max(learning_rate * 1e-3, 1e-7)
                # ReduceLR patience: 10% epochs (min=5, max=30)
                _rlr_patience = max(5, min(30, self._epochs // 10))
                callbacks.append(
                    tf.keras.callbacks.ReduceLROnPlateau(
                        monitor="val_loss",
                        factor=0.85,        # LR × 0.85 (کمی تندتر از 0.9)
                        patience=_rlr_patience,
                        verbose=0,
                        mode="min",
                        min_delta=1e-6,
                        cooldown=2,
                        min_lr=_min_lr,
                    )
                )
                # Phase 57: EarlyStopping — وقتی plateau زد متوقف بشه
                _es_patience = max(10, min(50, self._epochs // 5))
                _reporter_ref = self._progress
                _fold_ref = fold_info

                # EarlyStopping ساده — بدون subclass (serialize مشکل نداشته باشه)
                _es = tf.keras.callbacks.EarlyStopping(
                    monitor="val_loss",
                    patience=_es_patience,
                    mode="min",
                    min_delta=1e-6,
                    restore_best_weights=False,
                    verbose=0,
                )
                # wrapper برای گزارش به reporter
                _rep = _reporter_ref
                _fld = _fold_ref
                _orig_end = _es.on_train_end
                def _es_on_end(logs: Any = None, _es=_es, _rep=_rep, _fld=_fld) -> None:
                    _orig_end(logs)
                    if getattr(_es, "stopped_epoch", 0) > 0:
                        best = float(getattr(_es, "best", 0.0) or 0.0)
                        fn = getattr(_rep, "on_early_stop", None)
                        if callable(fn):
                            fn(_fld, _es.stopped_epoch, best)
                _es.on_train_end = _es_on_end  # type: ignore[method-assign]
                callbacks.append(_es)
            if not isinstance(self._progress, NullProgressReporter):
                callbacks.append(keras_progress_callback(self._progress, fold_info, self._epochs))
                # An epoch over 50,000 samples is thousands of batches and
                # several minutes; without this the log sits still between
                # epoch lines and looks hung.
                if hasattr(self._progress, "on_batch_end"):
                    # Phase 43: a streamed fold is an INFINITE tf.data
                    # dataset (it repeats so multi-epoch runs do not run
                    # dry), and len() on it raises "The dataset is
                    # infinite". The batch count is already known from
                    # the fold geometry, so ask arithmetic rather than
                    # the dataset.
                    batches_per_epoch = train_steps or max(
                        1, -(-train_size // max(self._batch_size, 1))
                    )
                    callbacks.append(
                        keras_batch_callback(
                            self._progress,
                            fold_info,
                            total_batches=batches_per_epoch,
                        )
                    )

            # Phase 57: initial_epoch برای همه fold ها
            # وقتی resume هست، همه fold ها از initial_epoch شروع میکنن
            fit_initial_epoch = self._initial_epoch if self._resume_weights else 0

            if train_y is None:
                # Streamed: the dataset already carries its labels and
                # its own batching.
                history = model.fit(
                    train_x,
                    validation_data=val_x,
                    epochs=self._epochs,
                    initial_epoch=fit_initial_epoch,
                    steps_per_epoch=train_steps,
                    validation_steps=val_steps,
                    verbose=self._verbose,
                    shuffle=False,
                    callbacks=callbacks,
                )
            else:
                history = model.fit(
                    train_x,
                    train_y,
                    validation_data=(val_x, val_y),
                    epochs=self._epochs,
                    initial_epoch=fit_initial_epoch,
                    batch_size=self._batch_size,
                    verbose=self._verbose,
                    callbacks=callbacks,
                )
            val_loss = float(history.history["val_loss"][-1])
            self.fold_history.append(val_loss)
            # Phase 36: Keras computes accuracy (or MAE) every epoch and
            # the trainer used to discard all of it, keeping only the
            # loss. "Is the model any good?" then had no answer anywhere
            # in the system. The final-epoch value of every metric is
            # kept per fold.
            fold_metrics = {
                name: float(values[-1]) for name, values in history.history.items() if values
            }
            if self._target_columns is not None:
                fold_metrics.update(
                    self._range_validation_metrics(
                        model,
                        val_x,
                        val_y,
                        val_steps,
                        fold.val_start,
                        fold.val_end,
                    )
                )
            self.fold_metrics.append(fold_metrics)
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

    #: Above this many windows a fold is streamed rather than materialised.
    #: 20,000 windows of 500x123 float32 is already 4.9 GB; below it the
    #: arrays are small enough that the simpler path stays faster.
    STREAM_THRESHOLD_BYTES = 512 * 1024 * 1024

    def _range_validation_metrics(
        self,
        model: Any,
        validation_x: Any,
        validation_y: Any,
        validation_steps: int,
        start: int,
        stop: int,
    ) -> Dict[str, float]:
        """Report high/low error separately from the aggregate MAE.

        Keras' multi-output MAE averages both bounds, which can hide a
        badly biased low or high prediction.  The validation labels are
        regenerated from the same flat series for streamed folds, so this
        diagnostic never changes the training data or the selected loss.
        """
        import numpy as np

        predictions = model.predict(
            validation_x,
            steps=validation_steps if validation_y is None else None,
            verbose=0,
        )
        if validation_y is None:
            labels: List[Any] = []
            for _, batch_y in self._generator().iter_batches(
                batch_size=self._batch_size,
                start=start,
                stop=stop,
            ):
                labels.append(batch_y)
            if not labels:
                return {}
            actual = np.concatenate(labels, axis=0)
        else:
            actual = np.asarray(validation_y)

        predicted = np.asarray(predictions)
        count = min(len(actual), len(predicted))
        if count < 1 or actual.shape[-1] < 2 or predicted.shape[-1] < 2:
            return {}
        actual = actual[:count, :2].astype(np.float64)
        predicted = predicted[:count, :2].astype(np.float64)
        error = predicted - actual
        return {
            "val_high_mae": float(np.mean(np.abs(error[:, 0]))),
            "val_low_mae": float(np.mean(np.abs(error[:, 1]))),
            "val_high_rmse": float(np.sqrt(np.mean(error[:, 0] ** 2))),
            "val_low_rmse": float(np.sqrt(np.mean(error[:, 1] ** 2))),
            "val_high_bias": float(np.mean(error[:, 0])),
            "val_low_bias": float(np.mean(error[:, 1])),
        }

    def _dataset_for(self, start: int, stop: int) -> tuple:
        """Training inputs for one fold, streamed when they are large.

        Returns ``(x, y, 0)`` for the in-memory path, or
        ``(dataset, None, steps_per_epoch)`` when the fold is streamed.
        The caller branches on ``y is None``.
        """
        count = max(stop - start, 0)
        estimated = count * self._window_size * self._n_features_cache * 4

        if not self._stream_all and estimated <= self.STREAM_THRESHOLD_BYTES:
            x, y = self._arrays(self._samples[start:stop])
            return x, y, 0

        generator = self._generator()
        batch = max(self._batch_size, 1)
        dataset = generator.to_tf_dataset(batch_size=batch, start=start, stop=stop, repeat=True)
        # With repeat() the dataset is infinite, so Keras must be told
        # where an epoch ends.
        steps = max(1, -(-count // batch))
        return dataset, None, steps

    def _generator(self):
        """A lazy window generator over the flat series (Phase 41)."""
        from ShadBotTrader.infrastructure.ai.window_generator import WindowGenerator

        if self._window_cache is None:
            targets = (
                self._target_columns if self._target_columns is not None else [self._target_column]
            )
            self._window_cache = WindowGenerator(
                series=self._series,
                target_columns=targets,
                window_size=self._window_size,
                horizon=0,
                stride=1,
                scale=True,
                classification=self._target_columns is None,
                sample_ends=self._sample_indices,
            )
        return self._window_cache

    def _arrays(self, samples) -> tuple:
        import numpy as np

        x = np.array([sample.features for sample in samples], dtype=np.float32)

        if self._target_columns is not None:
            if self._seq2seq:
                # فاز ۵۵: seq2seq — Y shape = [batch, window, n_targets]
                # از هر ROW در window، ستون‌های target رو بگیر
                # series[t] = [features..., high_off_t, low_off_t]
                # sample.features = window[:, :feature_count] (scaled)
                # target در هر row = series_row[target_columns]
                # ولی samples فقط features دارن — باید از _series بسازیم
                y = self._build_seq2seq_targets(samples, np)
                return x, y
            # Scalar regression
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

    def _build_seq2seq_targets(self, samples: Any, np: Any) -> Any:
        """Y tensor [batch, window, n_targets] برای seq2seq.

        هر row از window یه target داره:
          series[t][target_cols] = target برای کندل t (= high/low فردای t)
        این کار رو از raw series (نه scaled samples) انجام میدیم.
        """
        targets = self._target_columns or []
        n_t = len(targets)
        ws = self._window_size
        batch = []
        for sample in samples:
            # پیدا کردن index این window در series
            # sample.features shape = [ws, n_features]
            # ما باید target_columns رو از series بگیریم
            # sample.target_index = آخرین row index
            end_idx = getattr(sample, "target_index", None)
            if end_idx is None:
                # fallback: از target های scalar استفاده کن برای همه rows
                row_targets = [sample.targets or [0.0] * n_t] * ws
            else:
                start_idx = end_idx - ws + 1
                row_targets = [
                    [float(self._series[i][col]) for col in targets]
                    for i in range(max(0, start_idx), end_idx + 1)
                ]
                # padding اگه کمتر از ws بود
                while len(row_targets) < ws:
                    row_targets.insert(0, [0.0] * n_t)
            batch.append(row_targets)
        return np.array(batch, dtype=np.float32)

    @staticmethod
    def _tf_version() -> str:
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet import _require_tensorflow

        return _require_tensorflow().__version__


class _LazySampleCount:
    """Stands in for the samples list when the folds are streamed.

    ``expanding_split`` and the progress plan only ever ask how many
    windows exist. Building the windows to answer that question is what
    exhausted the machine, so this reports the count arithmetically and
    refuses to be indexed — anything that tries to slice it is a code
    path that has not been taught to stream.
    """

    __slots__ = ("_count",)

    def __init__(self, count: int) -> None:
        self._count = max(count, 0)

    def __len__(self) -> int:
        return self._count

    def __getitem__(self, item: object) -> None:  # pragma: no cover - guard
        raise RuntimeError(
            "This fold is streamed; its windows were deliberately never "
            "materialised. Use the tf.data path instead of indexing."
        )


def _EpochCheckpoint(callback: Any, model: Any, total_epochs: int) -> Any:
    """A Keras callback that hands the model out after every epoch.

    Training a real dataset takes hours. Persisting only at the very end
    means any interruption — a timeout, a closed laptop, Ctrl+C — throws
    away everything. Saving each epoch turns a lost run into a slightly
    older model.
    """
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet import _require_tensorflow

    tf = _require_tensorflow()

    class _Checkpoint(tf.keras.callbacks.Callback):  # type: ignore[misc,name-defined]
        def on_epoch_end(self, epoch: int, logs: Any = None) -> None:
            try:
                callback(self.model, epoch, dict(logs or {}), total_epochs)
            except Exception:
                # A failing checkpoint must never abort training that is
                # otherwise going fine.
                pass

    return _Checkpoint()


def _notify(reporter: object, hook: str, *args: object) -> None:
    """Call an optional reporter hook.

    The reporter contract grew in Phase 39 (preparation and batch
    hooks). A reporter written against the older, smaller contract is
    still valid — it simply observes less — so a missing hook is skipped
    rather than raising. Observation must never break training.
    """
    method = getattr(reporter, hook, None)
    if callable(method):
        method(*args)


def _load_weights_into(model: Any, weights_bytes: bytes) -> None:
    """Warm-start a compiled model from a saved .keras artifact (Phase 50).

    The saved artifact was produced by ``_serialize_model`` (a .keras
    file serialised to bytes). We deserialise it into a temporary model
    and copy the weights across. Architecture must match exactly — same
    number of layers, same shapes — which is guaranteed because the
    checkpoint was written by the same ``_build_compiled`` call with
    identical hyperparameters.
    """
    try:
        saved_model = _deserialize_model(weights_bytes)
        model.set_weights(saved_model.get_weights())
        print("      [resume] weights loaded from checkpoint OK")
        del saved_model
    except Exception as error:
        # Mismatched architecture or corrupt file: start from scratch
        # rather than crashing training entirely.
        print(f"      [resume] could not load weights: {error} — starting from scratch")


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
    depth_multiplier: int = 8,
    loss: str | None = None,
    metric: str | None = None,
    l2: float = 2.5e-4,
    dropout: float = 0.10,
    seq2seq: bool = False,
    horizon: int = 5,
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

    _is_regression = loss in (
        "mse", "mean_squared_error",
        "mae", "mean_absolute_error",
        "huber", "huber_loss",
    )
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
        l2=l2,
        dropout=dropout,
        is_regression=_is_regression,
        seq2seq=seq2seq,
        horizon=horizon,
    )

    if loss in ("mse", "mean_squared_error"):
        compiled_loss: object = tf.keras.losses.MeanSquaredError()
        compiled_metrics = [tf.keras.metrics.MeanAbsoluteError(name=metric or "mae")]
    elif loss in ("mae", "mean_absolute_error"):
        compiled_loss = tf.keras.losses.MeanAbsoluteError()
        compiled_metrics = [tf.keras.metrics.MeanSquaredError(name=metric or "mse")]
    elif loss in ("huber", "huber_loss"):
        # فاز ۵۴: Loss سه‌گانه (ایده از legacy/TimeSeriesPrediction2.py)
        #
        # ایده اصلی: ترکیب Huber + MAE + MSE با وزن‌بندی
        # legacy: loss_weights=[30, 60, 10] → 30*Huber + 60*MAE + 10*MSE
        #
        # چرا این ترکیب بهتره از یک loss تنها؟
        #   Huber (وزن اصلی): outlier-robust، smooth gradient
        #   MAE   (وزن بزرگ): انعطاف بیشتر، bias کمتر نسبت به MSE
        #   MSE   (وزن کوچک): gradient قوی برای خطاهای بزرگ در ابتدا
        #
        # delta Huber:
        #   target magnitude: +/-0.002 (+/-0.2% offset)
        #   val_mae ~ 0.0017 → delta=0.005 → δ/val_mae=2.9 → MSE mode [OK]
        # فاز ۵۴/۵۵: Loss سه‌گانه Huber+MAE+MSE
        # legacy weights: [30, 60, 10] → ما [3, 6, 1] (نسبت یکسان)
        _w_h, _w_m, _w_s = 3.0, 6.0, 1.0
        _w_sum = _w_h + _w_m + _w_s
        _is_seq2seq = seq2seq

        _huber_fn = tf.keras.losses.Huber(delta=0.005)

        def _weighted_loss(y_true_t: object, y_pred_t: object) -> object:
            """3*Huber + 6*MAE + 1*MSE — normalize شده."""
            h = _huber_fn(y_true_t, y_pred_t)
            m = tf.reduce_mean(tf.abs(tf.cast(y_true_t, tf.float32) - tf.cast(y_pred_t, tf.float32)))
            s = tf.reduce_mean(tf.square(tf.cast(y_true_t, tf.float32) - tf.cast(y_pred_t, tf.float32)))
            return (_w_h * h + _w_m * m + _w_s * s) / _w_sum

        try:
            import keras as _keras_reg
            _register_loss = _keras_reg.saving.register_keras_serializable
        except (ImportError, AttributeError):
            _register_loss = tf.keras.utils.register_keras_serializable

        @_register_loss(package="ShadBotTrader")
        class _RangeLoss(tf.keras.losses.Loss):
            """Weighted Huber+MAE+MSE.

            seq2seq (فاز ۵۵):
              40% loss کل sequence  +  60% loss آخرین timestep
              -> gradient قوی + focus روی پیش‌بینی فردا

            scalar (فاز ۵۴):
              loss معمولی روی 2 عدد خروجی
            """
            def get_config(self) -> dict:
                return super().get_config()

            def call(self, y_true: object, y_pred: object) -> object:
                if _is_seq2seq:
                    loss_all = _weighted_loss(y_true, y_pred)
                    # آخرین timestep: پیش‌بینی فردا
                    loss_tgt = _weighted_loss(
                        y_true[:, -1:, :],   # type: ignore[index]
                        y_pred[:, -1:, :],   # type: ignore[index]
                    )
                    return 0.4 * loss_all + 0.6 * loss_tgt
                return _weighted_loss(y_true, y_pred)

        compiled_loss = _RangeLoss(name="range_loss")
        if _is_seq2seq:
            # متریک MAE روی آخرین timestep خروجی seq2seq
            # ساده‌ترین حالت: از MeanAbsoluteError استاندارد Keras استفاده کن
            # ولی فقط روی آخرین timestep محاسبه کن
            # برای horizon=1: output[-1] = [high, low] فردا
            @_register_loss(package="ShadBotTrader")
            class _Seq2SeqMAE(tf.keras.metrics.Metric):
                """MAE روی آخرین timestep seq2seq.

                get_config/from_config پیاده‌سازی شده تا serialize درست کار کنه.
                """

                def __init__(self, name: str = "mae", **kw: object) -> None:
                    # name رو جداگانه می‌گیریم تا conflict نشه
                    # وقتی Keras از config لود می‌کنه، name رو پاس میده
                    super().__init__(name=name, **kw)  # type: ignore[call-arg]
                    self._mae_sum = self.add_weight(
                        name="s2s_sum", initializer="zeros"
                    )
                    self._mae_cnt = self.add_weight(
                        name="s2s_cnt", initializer="zeros"
                    )

                def get_config(self) -> dict:
                    cfg = super().get_config()
                    return cfg  # name در super().get_config() هست

                def update_state(  # type: ignore[override]
                    self, y_true: object, y_pred: object, sample_weight: object = None
                ) -> None:
                    true_last = y_true[:, -1, :]   # type: ignore[index]
                    pred_last = y_pred[:, -1, :]   # type: ignore[index]
                    mae_val = tf.reduce_mean(tf.abs(true_last - pred_last))
                    self._mae_sum.assign_add(tf.cast(mae_val, self._mae_sum.dtype))
                    self._mae_cnt.assign_add(1.0)

                def result(self) -> object:
                    return tf.math.divide_no_nan(self._mae_sum, self._mae_cnt)

                def reset_state(self) -> None:
                    self._mae_sum.assign(0.0)
                    self._mae_cnt.assign(0.0)

            compiled_metrics = [_Seq2SeqMAE()]
        else:
            compiled_metrics = [tf.keras.metrics.MeanAbsoluteError(name=metric or "mae")]
    else:
        # signal model: SparseCategoricalCrossentropy استاندارد
        # label_smoothing فقط در CategoricalCrossentropy (one-hot) کار میکنه
        # نه در Sparse (integer labels) — پس ساده نگه میداریم
        compiled_loss = tf.keras.losses.SparseCategoricalCrossentropy(
            from_logits=False,
        )
        compiled_metrics = [tf.keras.metrics.SparseCategoricalAccuracy(name="accuracy")]

    # فاز ۵۴: AdamW بجای Adam برای regression (ایده از legacy)
    # AdamW = Adam + Weight Decay مستقیم روی weights
    # بهتر از Adam+L2 regularizer چون decay مستقل از gradient scale‌بندی میشه
    # signal model: Adam ساده کافیه (classification)
    # range  model: AdamW بهتره (regression + L2 معادل ضمنی)
    # فاز ۵۷: AdamW برای هر دو regression و classification
    # weight_decay برای regression: 1e-4 (collapse کنترل)
    # weight_decay برای classification: 1e-5 (ملایم‌تر، label space محدودتره)
    is_regression_loss = loss in (
        "mse", "mean_squared_error",
        "mae", "mean_absolute_error",
        "huber", "huber_loss",
    )
    _wd = 1e-4 if is_regression_loss else 1e-5
    try:
        optimizer: object = tf.keras.optimizers.AdamW(
            learning_rate=learning_rate,
            weight_decay=_wd,
        )
    except AttributeError:
        try:
            optimizer = tf.keras.optimizers.experimental.AdamW(
                learning_rate=learning_rate,
                weight_decay=_wd,
            )
        except AttributeError:
            optimizer = tf.keras.optimizers.Adam(learning_rate=learning_rate)

    model.compile(
        optimizer=optimizer,
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
