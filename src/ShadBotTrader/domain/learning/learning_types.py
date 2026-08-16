"""Self-Learning domain enumerations (Phase 17).

The vocabulary of the controlled learning loop: what an experiment is
doing, what happened to a candidate, and why it was rejected.
"""

from __future__ import annotations

from enum import Enum


class ExperimentStatus(str, Enum):
    """Lifecycle of one learning experiment."""

    CREATED = "created"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CandidateStatus(str, Enum):
    """Where a candidate sits in the promotion pipeline.

    A candidate never jumps straight to PROMOTED: it must be evaluated,
    then validated out-of-sample, before a promotion gate may approve it.
    """

    PROPOSED = "proposed"
    EVALUATED = "evaluated"
    VALIDATED = "validated"
    REJECTED = "rejected"
    PROMOTED = "promoted"
    ROLLED_BACK = "rolled_back"


class ObjectiveDirection(str, Enum):
    """Whether a metric should be maximised or minimised."""

    MAXIMIZE = "maximize"
    MINIMIZE = "minimize"


class SearchStrategy(str, Enum):
    """How the parameter space is explored."""

    GRID = "grid"
    RANDOM = "random"


class RejectionReason(str, Enum):
    """Why a candidate did not make it through the gate.

    Recorded in the learning memory so the same dead end is not explored
    twice (Phase 17: Failure Memory).
    """

    WORSE_THAN_BASELINE = "worse_than_baseline"
    INSUFFICIENT_TRADES = "insufficient_trades"
    EXCESSIVE_DRAWDOWN = "excessive_drawdown"
    NEGATIVE_RETURN = "negative_return"
    UNSTABLE_OUT_OF_SAMPLE = "unstable_out_of_sample"
    FAILED_VALIDATION_FOLD = "failed_validation_fold"
    OVERFIT_SUSPECTED = "overfit_suspected"
    EVALUATION_FAILED = "evaluation_failed"


class ValidationOutcome(str, Enum):
    """Result of validating a candidate."""

    PASSED = "passed"
    FAILED = "failed"
    INCONCLUSIVE = "inconclusive"
