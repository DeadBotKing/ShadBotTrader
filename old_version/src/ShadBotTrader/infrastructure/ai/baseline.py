"""Deterministic NumPy baseline models (no ML framework required).

These exist so the full AI Platform pipeline (register -> train ->
evaluate -> store -> predict) is testable without TensorFlow, and serve
as sanity-check references for the real Wavenet model.
"""

from __future__ import annotations

import json
from typing import List, Sequence

from ShadBotTrader.domain.ai.inference import InferenceRequest
from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_types import PredictionType
from ShadBotTrader.domain.ai.ports import ModelPredictor, ModelTrainer
from ShadBotTrader.domain.ai.prediction import Confidence, Prediction
from ShadBotTrader.domain.ai.training_run import TrainingRun


class LastValueModel:
    """A baseline regressor that predicts the last close value unchanged.

    This is a classic random-walk benchmark for price series.
    """

    def fit(
        self, features: Sequence[Sequence[float]], targets: Sequence[float]
    ) -> "LastValueModel":
        # no learnable parameters by design — the payload is a marker
        return self


class BaselineTrainer(ModelTrainer):
    """Trains (i.e. records) a baseline model as an artifact."""

    @property
    def framework(self) -> str:
        return "numpy-baseline"

    def train(self, definition: ModelDefinition, run: TrainingRun) -> ModelArtifact:
        # The baseline has no parameters; the artifact carries the target
        # column and window size so prediction is deterministic.
        payload = json.dumps(
            {
                "kind": "last_value",
                "target_name": definition.target_name,
            }
        ).encode("utf-8")
        return ModelArtifact.create(
            model_id=definition.model_id,
            version=definition.version,
            framework=self.framework,
            framework_version="1.0",
            format="json",
            payload=payload,
            training_run_id=run.run_id,
        )


class BaselinePredictor(ModelPredictor):
    """Predicts with the baseline last-value model."""

    def predict(
        self,
        definition: ModelDefinition,
        artifact: ModelArtifact,
        request: InferenceRequest,
    ) -> Prediction:
        # window = request.features; last value of the target column
        target_index = _target_index(definition, request)
        value = float(request.features[-1][target_index]) if request.features else 0.0
        return Prediction(
            model_id=definition.model_id.value,
            model_version=definition.version.number,
            prediction_type=PredictionType.PRICE,
            value=value,
            confidence=Confidence(1.0),
            horizon=1,
        )


class DirectionModel:
    """A baseline direction classifier using the last close-to-close sign."""

    def predict_sign(self, features: List[List[float]], target_index: int) -> float:
        if len(features) < 2:
            return 0.0
        delta = features[-1][target_index] - features[-2][target_index]
        return 1.0 if delta > 0 else -1.0


def _target_index(definition: ModelDefinition, request: InferenceRequest) -> int:
    if request.feature_names and definition.target_name in request.feature_names:
        return request.feature_names.index(definition.target_name)
    return len(request.features[0]) - 1 if request.features and request.features[0] else 0
