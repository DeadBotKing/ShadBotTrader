"""Model identity and version value objects (Phase 13, sections 5, 9)."""

from __future__ import annotations

from typing import Any, Tuple

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class ModelId(ValueObject):
    """The implementation-independent identity of a model.

    Normalized to a lowercase snake label, e.g.
    ``gold_price_forecaster``. The id stays stable even when the model
    implementation changes over time.
    """

    def __init__(self, value: str) -> None:
        normalized = value.strip().lower().replace(" ", "_")
        if not normalized:
            raise ValidationError("ModelId must not be empty")
        self._id = normalized

    @property
    def value(self) -> str:
        return self._id

    def _value(self) -> Tuple[Any, ...]:
        return (self._id,)

    def __str__(self) -> str:
        return self._id


class ModelVersion(ValueObject):
    """An immutable, monotonic model version (section 9).

    Every behaviour-affecting change (architecture, features, target,
    hyperparameters, data) must produce a new version.
    """

    def __init__(self, number: int) -> None:
        if isinstance(number, bool) or not isinstance(number, int) or number < 1:
            raise ValidationError(f"ModelVersion must be >= 1, got {number!r}")
        self._number = number

    @property
    def number(self) -> int:
        return self._number

    def next(self) -> "ModelVersion":
        return ModelVersion(self._number + 1)

    def _value(self) -> Tuple[Any, ...]:
        return (self._number,)

    def __str__(self) -> str:
        return str(self._number)
