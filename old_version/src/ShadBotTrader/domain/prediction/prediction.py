"""Prediction value object produced by the AI platform."""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.market.timestamp import Timestamp


class PredictionType(str, Enum):
    """The kind of value a prediction carries."""

    DIRECTION = "direction"
    PRICE = "price"
    PROBABILITY = "probability"


class Prediction(ValueObject):
    """An immutable model prediction with its confidence.

    The model that produced the prediction and the time it was generated
    are recorded for traceability. The ``metadata`` mapping is auxiliary
    provenance information and does not participate in equality.
    """

    def __init__(
        self,
        model_id: str,
        prediction_type: PredictionType,
        value: float,
        confidence: float,
        generated_at: Timestamp,
        metadata: Dict[str, Any] | None = None,
    ) -> None:
        if not model_id.strip():
            raise ValidationError("model_id must not be empty")
        if not 0.0 <= confidence <= 1.0:
            raise ValidationError(f"confidence must be in [0, 1], got {confidence}")
        self._model_id = model_id
        self._prediction_type = prediction_type
        self._prediction_value = value
        self._confidence = confidence
        self._generated_at = generated_at
        self._metadata = dict(metadata or {})

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def prediction_type(self) -> PredictionType:
        return self._prediction_type

    @property
    def value(self) -> float:
        return self._prediction_value

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def generated_at(self) -> Timestamp:
        return self._generated_at

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    def _value(self) -> tuple[Any, ...]:
        return (
            self._model_id,
            self._prediction_type,
            self._prediction_value,
            self._confidence,
            self._generated_at,
        )
