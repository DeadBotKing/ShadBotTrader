"""Evaluation metrics (Phase 13, sections 42-45)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class EvaluationMetrics:
    """The metrics of one evaluation run, keyed by name.

    Supports regression (MAE/RMSE/MAPE), classification
    (accuracy/precision/recall/f1) and trading metrics (hit rate,
    profit factor). Only computed metrics are present in the mapping.
    """

    model_id: str
    model_version: int
    metrics: Dict[str, float] = field(default_factory=dict)
    sample_count: int = 0
    notes: str = ""

    def with_metric(self, name: str, value: float) -> "EvaluationMetrics":
        """Return a copy with one additional metric."""
        updated = dict(self.metrics)
        updated[name] = value
        return EvaluationMetrics(
            model_id=self.model_id,
            model_version=self.model_version,
            metrics=updated,
            sample_count=self.sample_count,
            notes=self.notes,
        )

    def get(self, name: str) -> Optional[float]:
        return self.metrics.get(name)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "metrics": dict(self.metrics),
            "sample_count": self.sample_count,
            "notes": self.notes,
        }


@dataclass(frozen=True)
class EvaluationRecord:
    """A stored evaluation result for one model version."""

    run_id: str
    metrics: EvaluationMetrics
    fold_count: int = 1
    evaluated_at: str = ""
    fold_results: List[EvaluationMetrics] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "metrics": self.metrics.to_dict(),
            "fold_count": self.fold_count,
            "evaluated_at": self.evaluated_at,
            "fold_results": [fold.to_dict() for fold in self.fold_results],
        }
