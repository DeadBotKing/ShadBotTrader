"""Feature quality score and report (Phase 12, sections 45-48)."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any, List

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class FeatureIssueCode(str, Enum):
    """Feature quality issue codes."""

    NAN_AFTER_WARMUP = "NAN_AFTER_WARMUP"
    INFINITE_VALUE = "INFINITE_VALUE"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    TIMESTAMP_MISALIGNED = "TIMESTAMP_MISALIGNED"
    DUPLICATE_TIMESTAMP = "DUPLICATE_TIMESTAMP"
    EMPTY_RESULT = "EMPTY_RESULT"


@dataclass(frozen=True)
class FeatureQualityIssue:
    """A single feature-quality problem."""

    code: FeatureIssueCode
    message: str
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code.value, "message": self.message, "count": self.count}


class FeatureQualityScore(ValueObject):
    """0..100 scores for completeness, validity, stability, freshness."""

    def __init__(
        self,
        completeness: Decimal,
        validity: Decimal,
        stability: Decimal,
        freshness: Decimal,
    ) -> None:
        self._completeness = self._coerce(completeness, "completeness")
        self._validity = self._coerce(validity, "validity")
        self._stability = self._coerce(stability, "stability")
        self._freshness = self._coerce(freshness, "freshness")
        for name, value in (
            ("completeness", self._completeness),
            ("validity", self._validity),
            ("stability", self._stability),
            ("freshness", self._freshness),
        ):
            if not 0 <= value <= 100:
                raise ValidationError(f"{name} must be in [0, 100], got {value}")

    @staticmethod
    def _coerce(value: object, name: str) -> Decimal:
        from decimal import InvalidOperation

        try:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, float):
                return Decimal(str(value))
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"Invalid {name} value: {value!r}") from exc

    @property
    def completeness(self) -> Decimal:
        return self._completeness

    @property
    def validity(self) -> Decimal:
        return self._validity

    @property
    def stability(self) -> Decimal:
        return self._stability

    @property
    def freshness(self) -> Decimal:
        return self._freshness

    @property
    def overall(self) -> Decimal:
        total = self._completeness + self._validity + self._stability + self._freshness
        return (total / Decimal(4)).quantize(Decimal("0.01"))

    def _value(self):
        return (self._completeness, self._validity, self._stability, self._freshness)

    def to_dict(self) -> dict[str, Any]:
        return {
            "completeness": float(self._completeness),
            "validity": float(self._validity),
            "stability": float(self._stability),
            "freshness": float(self._freshness),
            "overall": float(self.overall),
        }


@dataclass(frozen=True)
class FeatureQualityReport:
    """The result of validating a computed feature."""

    score: FeatureQualityScore
    issues: List[FeatureQualityIssue] = field(default_factory=list)

    @property
    def is_empty(self) -> bool:
        return any(issue.code is FeatureIssueCode.EMPTY_RESULT for issue in self.issues)

    @property
    def has_fatal(self) -> bool:
        """True when the feature is unusable (empty, all-NaN, misaligned)."""
        return any(
            issue.code
            in (
                FeatureIssueCode.EMPTY_RESULT,
                FeatureIssueCode.TIMESTAMP_MISALIGNED,
                FeatureIssueCode.INFINITE_VALUE,
            )
            for issue in self.issues
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }
