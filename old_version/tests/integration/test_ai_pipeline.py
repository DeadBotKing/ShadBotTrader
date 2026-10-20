"""End-to-end tests for the AI Platform (baseline — framework-free)."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from ShadBotTrader.application.services.model_training_service import (
    ModelTrainingService,
)
from ShadBotTrader.application.services.prediction_service import PredictionService
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.ai.inference import InferenceRequest
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.ai.baseline import BaselinePredictor, BaselineTrainer
from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
    FilesystemArtifactStore,
)
from ShadBotTrader.infrastructure.ai.in_memory_model_registry import (
    InMemoryModelRegistry,
)
from ShadBotTrader.infrastructure.ai.training_run_recorder import (
    InMemoryTrainingRunRepository,
)


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


def _candles(count: int = 30) -> list[Candle]:
    start = datetime(2024, 1, 2, 8, 0, tzinfo=timezone.utc)
    candles = []
    for i in range(count):
        close = Decimal(str(2000 + i))
        candles.append(
            Candle(
                symbol=Symbol("XAUUSD_i"),
                timeframe=Timeframe("5M"),
                open_time=Timestamp(start + i * timedelta(minutes=5)),
                open_price=Price(close - 1),
                high=Price(close + 2),
                low=Price(close - 2),
                close=Price(close),
                volume=Decimal("100"),
            )
        )
    return candles


def test_full_training_and_prediction_pipeline(tmp_path):
    event_bus = EventBus()
    trained_events = []
    event_bus.subscribe("ModelTrained", lambda e: trained_events.append(e))

    registry = InMemoryModelRegistry()
    store = FilesystemArtifactStore(tmp_path)
    runs = InMemoryTrainingRunRepository()
    service = ModelTrainingService(
        registry=registry, artifact_store=store, run_repository=runs, event_bus=event_bus
    )

    outcome = service.train(
        definition=_definition(),
        trainer=BaselineTrainer(),
        evaluator=None,
        dataset_version=1,
        seed=42,
    )

    assert len(trained_events) == 1
    assert trained_events[0].payload["model_id"] == "price_forecaster"
    assert store.exists(ModelId("price_forecaster"), ModelVersion(1))
    assert runs.get(outcome.run_id) is not None

    # prediction service
    prediction_service = PredictionService(registry=registry, artifact_store=store)
    request = InferenceRequest(
        model_id="price_forecaster",
        model_version=1,
        features=[[10.0, 2000.0], [11.0, 2005.0]],
        feature_names=["x", "close"],
    )
    result = prediction_service.predict(BaselinePredictor(), request)
    assert result.prediction.value == 2005.0
    assert result.latency_ms >= 0.0


def test_prediction_service_unknown_model_raises(tmp_path):
    service = PredictionService(
        registry=InMemoryModelRegistry(),
        artifact_store=FilesystemArtifactStore(tmp_path),
    )
    request = InferenceRequest(model_id="unknown", model_version=1, features=[[1.0]])
    try:
        service.predict(BaselinePredictor(), request)
        raise AssertionError("expected LookupError")
    except LookupError:
        pass
