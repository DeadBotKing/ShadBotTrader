"""Roll-forward (walk-forward) evaluation over a trained model.

The trained model predicts every validation window of a walk-forward
plan; metrics are computed per fold and aggregated. This mirrors the
evaluation methodology of Phase 13 (sections 46-47) without leaking
future data into any validation window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Sequence

from ShadBotTrader.domain.ai.evaluation import EvaluationMetrics, EvaluationRecord
from ShadBotTrader.domain.ai.inference import InferenceRequest
from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.ports import ModelEvaluator, ModelPredictor
from ShadBotTrader.domain.ai.training_run import TrainingRun
from ShadBotTrader.infrastructure.ai.data_windowing import build_samples
from ShadBotTrader.infrastructure.ai.metrics import classification_metrics
from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split


@dataclass(frozen=True)
class FoldEvaluation:
    """Per-fold evaluation result."""

    fold_index: int
    metrics: EvaluationMetrics


class RollForwardEvaluator(ModelEvaluator):
    """Evaluates a model with walk-forward validation windows."""

    def __init__(
        self,
        predictor: ModelPredictor,
        series: Sequence[Sequence[float]],
        target_column: int,
        window_size: int,
        val_size: int = 4,
        step: int = 2,
        min_train_size: int = 8,
        num_classes: int = 2,
        max_folds: int | None = None,
    ) -> None:
        self._predictor = predictor
        self._series = [list(row) for row in series]
        self._target_column = target_column
        self._window_size = window_size
        self._val_size = val_size
        self._step = step
        self._min_train_size = min_train_size
        self._num_classes = num_classes
        self._max_folds = max_folds

    def evaluate(
        self,
        definition: ModelDefinition,
        artifact: ModelArtifact,
        run: TrainingRun,
    ) -> EvaluationMetrics:
        """Evaluate and return the aggregated metrics (plus per-fold)."""
        record = self.evaluate_record(definition, artifact, run)
        return record.metrics

    def evaluate_record(
        self,
        definition: ModelDefinition,
        artifact: ModelArtifact,
        run: TrainingRun,
    ) -> EvaluationRecord:
        """Evaluate and return the full record with per-fold metrics."""
        samples = build_samples(
            self._series,
            window_size=self._window_size,
            target_column=self._target_column,
            scale=False,
            # Must mirror the trainer: the target column is not an input
            # feature, otherwise the model would be fed the answer.
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
            # Mirror the trainer: evaluate the same most-recent folds.
            folds = folds[-self._max_folds :]

        fold_metrics: List[EvaluationMetrics] = []
        for fold in folds:
            actual: List[int] = []
            predicted: List[int] = []
            for index in range(fold.val_start, fold.val_end):
                sample = samples[index]
                request = InferenceRequest(
                    model_id=definition.model_id.value,
                    model_version=definition.version.number,
                    features=sample.features,
                    feature_names=[],
                )
                prediction = self._predictor.predict(definition, artifact, request)
                actual.append(int(sample.target) if sample.target is not None else 0)
                predicted.append(int(round(prediction.value)))
            metrics_values = classification_metrics(actual, predicted, self._num_classes)
            fold_metrics.append(
                EvaluationMetrics(
                    model_id=definition.model_id.value,
                    model_version=definition.version.number,
                    metrics=metrics_values,
                    sample_count=len(actual),
                )
            )

        aggregate = _aggregate(fold_metrics)
        return EvaluationRecord(
            run_id=run.run_id,
            metrics=aggregate,
            fold_count=len(fold_metrics),
            fold_results=fold_metrics,
        )


def _aggregate(fold_metrics: Sequence[EvaluationMetrics]) -> EvaluationMetrics:
    if not fold_metrics:
        return EvaluationMetrics(model_id="", model_version=0, metrics={}, sample_count=0)
    keys = set(fold_metrics[0].metrics.keys())
    aggregated: dict[str, float] = {}
    for key in keys:
        values = [fold.metrics.get(key, 0.0) for fold in fold_metrics]
        aggregated[key] = sum(values) / len(values)
    return EvaluationMetrics(
        model_id=fold_metrics[0].model_id,
        model_version=fold_metrics[0].model_version,
        metrics=aggregated,
        sample_count=sum(fold.sample_count for fold in fold_metrics),
    )
