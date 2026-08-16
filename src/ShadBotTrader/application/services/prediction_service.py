"""Application service: load a model artifact and run inference."""

from __future__ import annotations

from time import perf_counter

from ShadBotTrader.domain.ai.inference import InferenceRequest, InferenceResult
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.ports import ModelArtifactStore, ModelPredictor, ModelRegistry


class PredictionService:
    """Serves predictions from registered, trained models."""

    def __init__(
        self,
        registry: ModelRegistry,
        artifact_store: ModelArtifactStore,
    ) -> None:
        self._registry = registry
        self._artifact_store = artifact_store

    def predict(
        self,
        predictor: ModelPredictor,
        request: InferenceRequest,
    ) -> InferenceResult:
        """Run inference and measure latency."""
        model_id = ModelId(request.model_id)
        version = ModelVersion(request.model_version)

        definition: ModelDefinition | None = self._registry.get(model_id, version)
        if definition is None:
            raise LookupError(f"Model {model_id} v{version.number} is not registered")

        artifact = self._artifact_store.load(model_id, version)
        if artifact is None:
            raise LookupError(f"Model {model_id} v{version.number} artifact not found")

        start = perf_counter()
        prediction = predictor.predict(definition, artifact, request)
        latency_ms = (perf_counter() - start) * 1000.0

        return InferenceResult(request=request, prediction=prediction, latency_ms=latency_ms)
