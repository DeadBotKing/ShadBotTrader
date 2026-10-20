"""Phase 116 hybrid-head predictor adapter tests."""

from __future__ import annotations

import pickle

import numpy as np
import pytest

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.prediction_target import HybridSignalClass
from ShadBotTrader.infrastructure.ai.hybrid_head_predictor import HybridHeadPredictor


class FakeModel:
    classes_ = np.array([2, 0, 1])

    def predict_proba(self, values):
        assert values.shape == (1, 2)
        # raw order is BUY, SELL, HOLD; predictor must align to SELL,HOLD,BUY.
        return np.array([[0.70, 0.20, 0.10]])


def artifact() -> ModelArtifact:
    payload = pickle.dumps(
        {
            "model": FakeModel(),
            "feature_names": ["a", "b"],
            "classes": [2, 0, 1],
        }
    )
    return ModelArtifact.create(
        model_id=ModelId("gold_hybrid_lightgbm_head_5m"),
        version=ModelVersion(1),
        framework="fake",
        framework_version="fake",
        format="pickle",
        payload=payload,
        training_run_id="test",
    )


def test_probabilities_are_aligned_to_sell_hold_buy():
    predictor = HybridHeadPredictor()

    probabilities = predictor.probabilities(artifact(), [{"a": 1.0, "b": 2.0}])

    assert probabilities[0].tolist() == pytest.approx([0.20, 0.10, 0.70])


def test_forecast_carries_model_identity_and_three_class_prediction():
    predictor = HybridHeadPredictor(horizon=288, timeframe="5M")

    forecast = predictor.forecast(artifact(), {"a": 1.0, "b": 2.0}, generated_at="now")

    assert forecast.predicted_class is HybridSignalClass.BUY
    assert forecast.model_id == "gold_hybrid_lightgbm_head_5m"
    assert forecast.model_version == 1
    assert forecast.generated_at == "now"


def test_missing_or_bad_values_are_zero_filled():
    predictor = HybridHeadPredictor()

    probabilities = predictor.probabilities(artifact(), [{"a": "bad"}])

    assert probabilities.shape == (1, 3)
