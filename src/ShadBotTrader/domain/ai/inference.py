"""Inference request/result contracts (Phase 13, sections 21-22)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List

from ShadBotTrader.domain.ai.prediction import Prediction
from ShadBotTrader.domain.common.errors import ValidationError


@dataclass(frozen=True)
class InferenceRequest:
    """A request to run one model over one input window.

    ``features`` is the window: a list of time steps, each a list of
    feature-column values (``[timestep][column]``).
    """

    model_id: str
    model_version: int
    features: List[List[float]]
    feature_names: List[str] = field(default_factory=list)
    request_id: str = ""

    def __post_init__(self) -> None:
        if not self.features:
            raise ValidationError("InferenceRequest features must not be empty")

    @property
    def time_steps(self) -> int:
        return len(self.features)

    @property
    def feature_count(self) -> int:
        return len(self.features[0]) if self.features else 0


@dataclass(frozen=True)
class InferenceResult:
    """The outcome of an inference request."""

    request: InferenceRequest
    prediction: Prediction
    latency_ms: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request.request_id,
            "model_id": self.request.model_id,
            "model_version": self.request.model_version,
            "prediction": self.prediction.to_dict(),
            "latency_ms": self.latency_ms,
        }
