"""Prediction value objects (Phase 13, sections 17-22)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from ShadBotTrader.domain.ai.model_types import PredictionType
from ShadBotTrader.domain.common.errors import ValidationError


class Confidence:
    """A probability in [0, 1] carried by every prediction."""

    def __init__(self, value: float) -> None:
        if not 0.0 <= value <= 1.0:
            raise ValidationError(f"Confidence must be in [0, 1], got {value}")
        self._value = value

    @property
    def value(self) -> float:
        return self._value

    def __float__(self) -> float:
        return self._value


@dataclass(frozen=True)
class Prediction:
    """A single model prediction with confidence and horizon."""

    model_id: str
    model_version: int
    prediction_type: PredictionType
    value: float
    confidence: Confidence
    horizon: int = 1
    generated_at: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "model_id": self.model_id,
            "model_version": self.model_version,
            "prediction_type": self.prediction_type.value,
            "value": self.value,
            "confidence": float(self.confidence),
            "horizon": self.horizon,
            "generated_at": self.generated_at,
        }


@dataclass(frozen=True)
class PredictionBatch:
    """A batch of predictions over a time-ordered series."""

    predictions: tuple[Prediction, ...]

    def to_list(self) -> list[Dict[str, Any]]:
        return [prediction.to_dict() for prediction in self.predictions]
