"""Application service: orchestrate model training, storage and evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from ShadBotTrader.core.events.event import Event
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.ai.evaluation import EvaluationRecord
from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.ports import (
    ModelArtifactStore,
    ModelEvaluator,
    ModelRegistry,
    ModelTrainer,
    TrainingRunRepository,
)
from ShadBotTrader.domain.ai.training_run import TrainingRun

MODEL_TRAINED = "ModelTrained"
MODEL_EVALUATED = "ModelEvaluated"


@dataclass(frozen=True)
class TrainingOutcome:
    """The outcome of one training run."""

    run_id: str
    definition: ModelDefinition
    artifact: ModelArtifact
    evaluation: EvaluationRecord | None = None

    @property
    def checksum(self) -> str:
        return self.artifact.checksum


class ModelTrainingService:
    """Runs the train -> store -> evaluate -> record pipeline."""

    def __init__(
        self,
        registry: ModelRegistry,
        artifact_store: ModelArtifactStore,
        run_repository: TrainingRunRepository,
        event_bus: EventBus,
    ) -> None:
        self._registry = registry
        self._artifact_store = artifact_store
        self._run_repository = run_repository
        self._event_bus = event_bus

    def train(
        self,
        definition: ModelDefinition,
        trainer: ModelTrainer,
        evaluator: ModelEvaluator | None,
        dataset_version: int,
        seed: int = 42,
    ) -> TrainingOutcome:
        """Run one full training cycle for a model version."""
        run = TrainingRun(
            run_id=str(uuid4()),
            model_id=definition.model_id,
            model_version=definition.version,
            dataset_version=dataset_version,
            feature_set_name=definition.feature_set_name,
            feature_set_version=definition.feature_set_version,
            seed=seed,
            hyperparameters=dict(definition.hyperparameters),
        )
        self._run_repository.record(run)
        self._registry.register(definition)

        artifact = trainer.train(definition, run)
        self._artifact_store.save(artifact)

        self._event_bus.publish(
            Event(
                event_type=MODEL_TRAINED,
                source="ModelTrainingService",
                payload={
                    "model_id": definition.model_id.value,
                    "model_version": definition.version.number,
                    "run_id": run.run_id,
                    "checksum": artifact.checksum,
                    "framework": artifact.framework,
                },
            )
        )

        evaluation: EvaluationRecord | None = None
        if evaluator is not None:
            evaluation = evaluator.evaluate_record(definition, artifact, run)
            self._event_bus.publish(
                Event(
                    event_type=MODEL_EVALUATED,
                    source="ModelTrainingService",
                    payload={
                        "model_id": definition.model_id.value,
                        "model_version": definition.version.number,
                        "metrics": evaluation.metrics.to_dict(),
                    },
                )
            )

        return TrainingOutcome(
            run_id=run.run_id,
            definition=definition,
            artifact=artifact,
            evaluation=evaluation,
        )
