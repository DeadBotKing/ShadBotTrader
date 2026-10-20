"""Candidates and their evaluation records (Phase 17: Candidate System).

A candidate is a proposed configuration together with everything learned
about it. It carries its own history — in-sample score, out-of-sample
folds, verdicts — so a promotion decision can always be explained after
the fact.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.learning.learning_types import (
    CandidateStatus,
    RejectionReason,
    ValidationOutcome,
)
from ShadBotTrader.domain.learning.objective import is_penalty
from ShadBotTrader.domain.learning.parameter_space import CandidateConfiguration
from ShadBotTrader.domain.simulation.performance import PerformanceMetrics


class EvaluationRecord(ValueObject):
    """The outcome of running one configuration over one data window."""

    def __init__(
        self,
        label: str,
        score: Decimal,
        metrics: PerformanceMetrics,
        bars: int = 0,
    ) -> None:
        self._label = label
        self._score = score
        self._metrics = metrics
        self._bars = bars

    @property
    def label(self) -> str:
        """Which window this was: ``in_sample``, ``fold_2``, ..."""
        return self._label

    @property
    def score(self) -> Decimal:
        return self._score

    @property
    def metrics(self) -> PerformanceMetrics:
        return self._metrics

    @property
    def bars(self) -> int:
        return self._bars

    def _value(self) -> tuple[Any, ...]:
        return (self._label, self._score, self._metrics)

    def __str__(self) -> str:
        return f"{self._label}: score={self._score:.4f} trades={self._metrics.trade_count}"


class Candidate:
    """A proposed configuration and everything learned about it."""

    def __init__(
        self,
        candidate_id: str,
        configuration: CandidateConfiguration,
        metadata: Mapping[str, Any] | None = None,
    ) -> None:
        if not candidate_id.strip():
            raise ValidationError("candidate_id must not be empty")
        self._candidate_id = candidate_id.strip()
        self._configuration = configuration
        self._metadata: Dict[str, Any] = dict(metadata or {})
        self._status = CandidateStatus.PROPOSED
        self._in_sample: Optional[EvaluationRecord] = None
        self._out_of_sample: List[EvaluationRecord] = []
        self._rejection_reason: Optional[RejectionReason] = None
        self._notes: List[str] = []

    # -- identity -----------------------------------------------------------
    @property
    def candidate_id(self) -> str:
        return self._candidate_id

    @property
    def configuration(self) -> CandidateConfiguration:
        return self._configuration

    @property
    def metadata(self) -> Dict[str, Any]:
        return dict(self._metadata)

    @property
    def status(self) -> CandidateStatus:
        return self._status

    @property
    def rejection_reason(self) -> Optional[RejectionReason]:
        return self._rejection_reason

    @property
    def notes(self) -> List[str]:
        return list(self._notes)

    # -- evidence -----------------------------------------------------------
    @property
    def in_sample(self) -> Optional[EvaluationRecord]:
        return self._in_sample

    @property
    def out_of_sample(self) -> List[EvaluationRecord]:
        return list(self._out_of_sample)

    @property
    def in_sample_score(self) -> Optional[Decimal]:
        return self._in_sample.score if self._in_sample else None

    @property
    def penalised_fold_count(self) -> int:
        """Folds whose score was a sentinel rather than a measurement."""
        return sum(1 for record in self._out_of_sample if is_penalty(record.score))

    @property
    def has_penalised_folds(self) -> bool:
        """True when at least one fold produced no usable evidence."""
        return self.penalised_fold_count > 0

    @property
    def out_of_sample_score(self) -> Optional[Decimal]:
        """Mean score across validation folds, or None when untested.

        The mean is deliberate: a candidate that wins one fold and
        collapses in the others has not demonstrated anything.

        A fold scored with a sentinel penalty (too few trades to judge)
        is NOT averaged in — mixing a -1,000,000 marker with real scores
        would swamp them and produce a meaningless figure. Instead the
        sentinel propagates: a candidate with any unusable fold is itself
        unusable, and is reported at the penalty level.
        """
        if not self._out_of_sample:
            return None
        if self.has_penalised_folds:
            return min(record.score for record in self._out_of_sample)
        total = sum((record.score for record in self._out_of_sample), Decimal("0"))
        return total / Decimal(len(self._out_of_sample))

    @property
    def worst_fold_score(self) -> Optional[Decimal]:
        if not self._out_of_sample:
            return None
        return min(record.score for record in self._out_of_sample)

    @property
    def positive_fold_count(self) -> int:
        """How many validation folds produced a positive return."""
        return sum(1 for record in self._out_of_sample if record.metrics.total_return > 0)

    @property
    def total_out_of_sample_trades(self) -> int:
        return sum(record.metrics.trade_count for record in self._out_of_sample)

    @property
    def overfit_gap(self) -> Optional[Decimal]:
        """In-sample score minus out-of-sample score.

        A large positive gap is the classic overfitting signature: the
        configuration learned the training window rather than a pattern.

        Returns None when either side is a sentinel: the difference
        between a real score and a penalty marker measures nothing.
        """
        inside = self.in_sample_score
        outside = self.out_of_sample_score
        if inside is None or outside is None:
            return None
        if is_penalty(inside) or is_penalty(outside):
            return None
        return inside - outside

    # -- transitions ---------------------------------------------------------
    def record_in_sample(self, record: EvaluationRecord) -> None:
        self._in_sample = record
        if self._status is CandidateStatus.PROPOSED:
            self._status = CandidateStatus.EVALUATED

    def record_out_of_sample(self, record: EvaluationRecord) -> None:
        self._out_of_sample.append(record)

    def validate(self, outcome: ValidationOutcome, note: str = "") -> None:
        """Record the validation verdict."""
        if note:
            self._notes.append(note)
        if outcome is ValidationOutcome.PASSED:
            self._status = CandidateStatus.VALIDATED
        elif outcome is ValidationOutcome.FAILED:
            self._status = CandidateStatus.REJECTED

    def reject(self, reason: RejectionReason, note: str = "") -> None:
        """Reject the candidate with an explicit, machine-readable cause."""
        self._status = CandidateStatus.REJECTED
        self._rejection_reason = reason
        if note:
            self._notes.append(note)

    def promote(self) -> None:
        """Promote the candidate — only from VALIDATED.

        This guard is the structural expression of the Phase 17 rule that
        self-learning may never push an untested configuration forward.
        """
        if self._status is not CandidateStatus.VALIDATED:
            raise ValidationError(
                f"Cannot promote a candidate in state '{self._status.value}'; "
                f"it must pass validation first"
            )
        self._status = CandidateStatus.PROMOTED

    def roll_back(self, note: str = "") -> None:
        if note:
            self._notes.append(note)
        self._status = CandidateStatus.ROLLED_BACK

    def to_dict(self) -> Dict[str, Any]:
        def show(value: Optional[Decimal]) -> Optional[str]:
            return str(value) if value is not None else None

        return {
            "candidate_id": self._candidate_id,
            "configuration": self._configuration.values,
            "status": self._status.value,
            "in_sample_score": show(self.in_sample_score),
            "out_of_sample_score": show(self.out_of_sample_score),
            "worst_fold_score": show(self.worst_fold_score),
            "overfit_gap": show(self.overfit_gap),
            "folds": len(self._out_of_sample),
            "penalised_folds": self.penalised_fold_count,
            "rejection_reason": (self._rejection_reason.value if self._rejection_reason else None),
        }

    def __str__(self) -> str:
        return f"{self._candidate_id} [{self._status.value}] {self._configuration.signature}"


def best_candidate(
    candidates: Sequence[Candidate],
    maximize: bool = True,
) -> Optional[Candidate]:
    """Return the candidate with the best out-of-sample score.

    Candidates without out-of-sample evidence are skipped entirely —
    ranking on in-sample results is precisely how overfit configurations
    get promoted.
    """
    scored = [
        candidate
        for candidate in candidates
        if candidate.out_of_sample_score is not None
        and candidate.status is not CandidateStatus.REJECTED
    ]
    if not scored:
        return None
    key = lambda candidate: candidate.out_of_sample_score  # noqa: E731
    return max(scored, key=key) if maximize else min(scored, key=key)
