"""Tests for the baseline last-value model."""

from ShadBotTrader.domain.ai.inference import InferenceRequest
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
from ShadBotTrader.domain.ai.training_run import TrainingRun
from ShadBotTrader.infrastructure.ai.baseline import BaselinePredictor, BaselineTrainer


def _definition() -> ModelDefinition:
    return ModelDefinition(
        model_id=ModelId("price_forecaster"),
        version=ModelVersion(1),
        name="Price forecaster",
        model_type=ModelType.REGRESSION,
        family=ModelFamily.LINEAR,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        target_name="close",
        hyperparameters={},
    )


def test_baseline_trainer_produces_artifact():
    trainer = BaselineTrainer()
    run = TrainingRun(
        run_id="r1",
        model_id=ModelId("price_forecaster"),
        model_version=ModelVersion(1),
        dataset_version=1,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        seed=42,
    )
    artifact = trainer.train(_definition(), run)
    assert artifact.framework == "numpy-baseline"
    assert artifact.training_run_id == "r1"


def test_baseline_predictor_last_value():
    definition = _definition()
    trainer = BaselineTrainer()
    artifact = trainer.train(
        definition,
        TrainingRun(
            run_id="r1",
            model_id=ModelId("price_forecaster"),
            model_version=ModelVersion(1),
            dataset_version=1,
            feature_set_name="FXTradingFeatureSetV1",
            feature_set_version=1,
            seed=42,
        ),
    )
    predictor = BaselinePredictor()
    request = InferenceRequest(
        model_id="price_forecaster",
        model_version=1,
        features=[[10.0, 2000.0], [11.0, 2005.0]],
        feature_names=["x", "close"],
    )
    prediction = predictor.predict(definition, artifact, request)
    assert prediction.value == 2005.0  # last close unchanged
