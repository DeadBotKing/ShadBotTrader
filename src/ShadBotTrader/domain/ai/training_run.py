"""Training run ledger (Phase 13, sections 33-34, 40)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict

from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion


class TrainingRunStatus(str, Enum):
    """The lifecycle status of a training run."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class TrainingRun:
    """A single, reproducible training run (section 33).

    Records everything required to reproduce the run: seed, dataset
    version, feature set version, hyperparameters and split strategy
    (section 34). Immutable once created; status is tracked separately.
    """

    run_id: str
    model_id: ModelId
    model_version: ModelVersion
    dataset_version: int
    feature_set_name: str
    feature_set_version: int
    seed: int
    hyperparameters: Dict[str, Any] = field(default_factory=dict)
    started_at: datetime = field(default_factory=lambda: datetime.now().astimezone())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "model_id": self.model_id.value,
            "model_version": self.model_version.number,
            "dataset_version": self.dataset_version,
            "feature_set_name": self.feature_set_name,
            "feature_set_version": self.feature_set_version,
            "seed": self.seed,
            "hyperparameters": dict(self.hyperparameters),
            "started_at": self.started_at.isoformat(),
        }
