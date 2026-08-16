"""Ports (contracts) of the AI domain (Phase 13, sections 49, 54, 59-62)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ShadBotTrader.domain.ai.evaluation import EvaluationMetrics, EvaluationRecord
from ShadBotTrader.domain.ai.inference import InferenceRequest
from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.prediction import Prediction
from ShadBotTrader.domain.ai.training_run import TrainingRun


class ModelRegistry(ABC):
    """Catalog of model definitions and lifecycle status (section 49)."""

    @abstractmethod
    def register(self, definition: ModelDefinition) -> None:
        """Record a model definition."""

    @abstractmethod
    def get(self, model_id: ModelId, version: ModelVersion) -> Optional[ModelDefinition]:
        """Return the definition for a model version, or None."""

    @abstractmethod
    def latest_version(self, model_id: ModelId) -> Optional[ModelVersion]:
        """Return the latest registered version of a model."""

    @abstractmethod
    def list_all(self) -> List[ModelDefinition]:
        """Return every registered definition."""


class ModelArtifactStore(ABC):
    """Persistence contract for model artifacts (section 10)."""

    @abstractmethod
    def save(self, artifact: ModelArtifact) -> None:
        """Persist an artifact immutably."""

    @abstractmethod
    def load(self, model_id: ModelId, version: ModelVersion) -> Optional[ModelArtifact]:
        """Load an artifact, or None when absent."""

    @abstractmethod
    def exists(self, model_id: ModelId, version: ModelVersion) -> bool:
        """Return True when the artifact exists."""


class ModelTrainer(ABC):
    """Trains one model version and returns its artifact (section 60)."""

    @property
    @abstractmethod
    def framework(self) -> str:
        """The framework this trainer uses, e.g. ``tensorflow``."""

    @abstractmethod
    def train(self, definition: ModelDefinition, run: TrainingRun) -> ModelArtifact:
        """Train ``definition`` and produce an immutable artifact."""


class ModelEvaluator(ABC):
    """Evaluates a trained model on a labeled dataset (section 61)."""

    @abstractmethod
    def evaluate_record(
        self,
        definition: ModelDefinition,
        artifact: ModelArtifact,
        run: TrainingRun,
    ) -> EvaluationRecord:
        """Return the full evaluation record (with per-fold metrics)."""

    def evaluate(
        self,
        definition: ModelDefinition,
        artifact: ModelArtifact,
        run: TrainingRun,
    ) -> EvaluationMetrics:
        """Return the aggregated evaluation metrics."""
        return self.evaluate_record(definition, artifact, run).metrics


class ModelPredictor(ABC):
    """Runs inference with a trained model (section 62)."""

    @abstractmethod
    def predict(
        self,
        definition: ModelDefinition,
        artifact: ModelArtifact,
        request: InferenceRequest,
    ) -> Prediction:
        """Produce a prediction for ``request``."""


class TrainingRunRepository(ABC):
    """Stores training-run records for reproducibility."""

    @abstractmethod
    def record(self, run: TrainingRun) -> None:
        """Record a training run."""

    @abstractmethod
    def get(self, run_id: str) -> Optional[TrainingRun]:
        """Return a training run by id, or None."""

    @abstractmethod
    def list_for_model(self, model_id: ModelId) -> List[TrainingRun]:
        """Return all training runs for a model."""
