"""Data-quality value objects: scores, issues and reports."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from enum import Enum
from typing import Any, List, Tuple

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject


class IssueSeverity(str, Enum):
    """How serious a data-quality issue is."""

    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass(frozen=True)
class QualityIssue:
    """A single detected data-quality problem."""

    code: str
    severity: IssueSeverity
    message: str
    count: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Return the issue as a JSON-serialisable mapping."""
        return {
            "code": self.code,
            "severity": self.severity.value,
            "message": self.message,
            "count": self.count,
        }


class QualityScore(ValueObject):
    """An aggregate 0..100 quality score built from five dimensions."""

    def __init__(
        self,
        completeness: Decimal,
        consistency: Decimal,
        validity: Decimal,
        timeliness: Decimal,
        uniqueness: Decimal,
    ) -> None:
        self._completeness = self._coerce(completeness, "completeness")
        self._consistency = self._coerce(consistency, "consistency")
        self._validity = self._coerce(validity, "validity")
        self._timeliness = self._coerce(timeliness, "timeliness")
        self._uniqueness = self._coerce(uniqueness, "uniqueness")
        for name, value in (
            ("completeness", self._completeness),
            ("consistency", self._consistency),
            ("validity", self._validity),
            ("timeliness", self._timeliness),
            ("uniqueness", self._uniqueness),
        ):
            if not 0 <= value <= 100:
                raise ValidationError(f"{name} must be in [0, 100], got {value}")

    @staticmethod
    def _coerce(value: Decimal | int | float | str, name: str) -> Decimal:
        try:
            if isinstance(value, Decimal):
                return value
            if isinstance(value, float):
                return Decimal(str(value))
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValidationError(f"Invalid {name} value: {value!r}") from exc

    @property
    def completeness(self) -> Decimal:
        return self._completeness

    @property
    def consistency(self) -> Decimal:
        return self._consistency

    @property
    def validity(self) -> Decimal:
        return self._validity

    @property
    def timeliness(self) -> Decimal:
        return self._timeliness

    @property
    def uniqueness(self) -> Decimal:
        return self._uniqueness

    @property
    def overall(self) -> Decimal:
        """The unweighted mean of the five dimensions, rounded to 2 dp."""
        total = (
            self._completeness
            + self._consistency
            + self._validity
            + self._timeliness
            + self._uniqueness
        )
        return (total / Decimal(5)).quantize(Decimal("0.01"))

    def _value(self) -> Tuple[Any, ...]:
        return (
            self._completeness,
            self._consistency,
            self._validity,
            self._timeliness,
            self._uniqueness,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the score as a JSON-serialisable mapping."""
        return {
            "completeness": float(self._completeness),
            "consistency": float(self._consistency),
            "validity": float(self._validity),
            "timeliness": float(self._timeliness),
            "uniqueness": float(self._uniqueness),
            "overall": float(self.overall),
        }


@dataclass(frozen=True)
class QualityReport:
    """The result of running the quality engine over a dataset."""

    score: QualityScore
    issues: List[QualityIssue] = field(default_factory=list)

    @property
    def has_critical(self) -> bool:
        """True when at least one critical issue was detected."""
        return any(issue.severity is IssueSeverity.CRITICAL for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        """Return the report as a JSON-serialisable mapping."""
        return {
            "score": self.score.to_dict(),
            "issues": [issue.to_dict() for issue in self.issues],
        }
