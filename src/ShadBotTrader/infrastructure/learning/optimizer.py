"""Walk-forward optimiser (Phase 17: Parameter Search + Walk Forward Validation).

The whole point of this module is to make it *hard* to fool yourself:

1. every candidate is scored on the **in-sample** window only
2. the top few are re-tested on **out-of-sample** folds they never saw
3. ranking for promotion uses out-of-sample results exclusively
4. the promotion gate compares against the baseline and can still refuse

A search that ranked on in-sample scores would reliably "discover"
configurations that memorised the training window. This one cannot.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, List, Optional, Sequence

from ShadBotTrader.domain.learning.candidate import (
    Candidate,
    EvaluationRecord,
    best_candidate,
)
from ShadBotTrader.domain.learning.experiment import LearningExperiment, WalkForwardPlan
from ShadBotTrader.domain.learning.learning_types import (
    CandidateStatus,
    ObjectiveDirection,
    RejectionReason,
    ValidationOutcome,
)
from ShadBotTrader.domain.learning.objective import LearningObjective
from ShadBotTrader.domain.learning.parameter_space import (
    CandidateConfiguration,
    ParameterSpace,
)
from ShadBotTrader.domain.learning.ports import (
    CandidateEvaluator,
    CandidateGenerator,
    LearningMemory,
    NullOptimisationReporter,
    OptimisationReporter,
)
from ShadBotTrader.domain.learning.promotion import PromotionGate, PromotionVerdict


@dataclass(frozen=True)
class OptimisationResult:
    """Everything a completed search produced."""

    experiment: LearningExperiment
    baseline: Optional[Candidate]
    winner: Optional[Candidate]
    verdict: Optional[PromotionVerdict]
    evaluated: List[Candidate]
    validated: List[Candidate]

    @property
    def promoted(self) -> bool:
        return self.winner is not None and self.winner.status is CandidateStatus.PROMOTED

    def to_dict(self) -> dict[str, Any]:
        return {
            "experiment_id": self.experiment.experiment_id,
            "objective": self.experiment.objective_name,
            "evaluated": len(self.evaluated),
            "validated": len(self.validated),
            "promoted": self.promoted,
            "winner": self.winner.to_dict() if self.winner else None,
            "baseline": self.baseline.to_dict() if self.baseline else None,
            "verdict": self.verdict.reason if self.verdict else None,
        }


class WalkForwardOptimizer:
    """Searches a parameter space and validates the survivors honestly."""

    def __init__(
        self,
        generator: CandidateGenerator,
        evaluator: CandidateEvaluator,
        objective: LearningObjective,
        gate: Optional[PromotionGate] = None,
        memory: Optional[LearningMemory] = None,
        reporter: Optional[OptimisationReporter] = None,
        validate_top_n: int = 3,
    ) -> None:
        if validate_top_n < 1:
            raise ValueError("validate_top_n must be >= 1")
        self._generator = generator
        self._evaluator = evaluator
        self._objective = objective
        self._gate = gate or PromotionGate()
        self._memory = memory
        self._reporter = reporter or NullOptimisationReporter()
        self._validate_top_n = validate_top_n

    def optimise(
        self,
        experiment: LearningExperiment,
        space: ParameterSpace,
        series: Sequence[Any],
        baseline_configuration: Optional[CandidateConfiguration] = None,
    ) -> OptimisationResult:
        """Run the full search-validate-gate loop."""
        plan = experiment.plan
        configurations = self._generator.generate(space)
        experiment.start()
        self._reporter.on_search_start(experiment, len(configurations))

        # -- baseline: measured exactly like every candidate --------------
        baseline: Optional[Candidate] = None
        if baseline_configuration is not None:
            baseline = Candidate("baseline", baseline_configuration)
            self._measure_in_sample(baseline, plan, series)
            self._measure_out_of_sample(baseline, plan, series)
            experiment.set_baseline(baseline)

        # -- phase 1: score every candidate in sample ----------------------
        evaluated: List[Candidate] = []
        for index, configuration in enumerate(configurations, start=1):
            candidate = Candidate(f"cand-{index:03d}", configuration)
            try:
                self._measure_in_sample(candidate, plan, series)
            except Exception as error:  # a bad configuration must not kill the run
                candidate.reject(RejectionReason.EVALUATION_FAILED, str(error))
            experiment.add_candidate(candidate)
            evaluated.append(candidate)
            self._reporter.on_candidate_evaluated(candidate, index, len(configurations))

        # -- phase 2: validate only the in-sample leaders -------------------
        survivors = self._top_in_sample(evaluated)
        validated: List[Candidate] = []
        for candidate in survivors:
            try:
                self._measure_out_of_sample(candidate, plan, series)
            except Exception as error:
                candidate.reject(RejectionReason.EVALUATION_FAILED, str(error))
                continue
            candidate.validate(
                ValidationOutcome.PASSED,
                note=f"validated over {plan.fold_count} folds",
            )
            validated.append(candidate)
            self._reporter.on_validation(candidate)

        # -- phase 3: rank OUT OF SAMPLE and put it to the gate -------------
        maximize = self._objective.direction is ObjectiveDirection.MAXIMIZE
        winner = best_candidate(validated, maximize=maximize)

        verdict: Optional[PromotionVerdict] = None
        if winner is not None:
            baseline_score = baseline.out_of_sample_score if baseline else None
            verdict = self._gate.evaluate(winner, baseline_score)
            if verdict.approved:
                winner.promote()
            else:
                assert verdict.rejection_reason is not None
                winner.reject(verdict.rejection_reason, verdict.reason)

        self._remember(evaluated, baseline)
        experiment.complete()
        self._reporter.on_search_end(experiment, winner)

        return OptimisationResult(
            experiment=experiment,
            baseline=baseline,
            winner=winner,
            verdict=verdict,
            evaluated=evaluated,
            validated=validated,
        )

    # -- helpers ------------------------------------------------------------
    def _measure_in_sample(
        self,
        candidate: Candidate,
        plan: WalkForwardPlan,
        series: Sequence[Any],
    ) -> None:
        record = self._evaluator.evaluate(
            candidate.configuration, plan.in_sample, series, "in_sample"
        )
        candidate.record_in_sample(record)

    def _measure_out_of_sample(
        self,
        candidate: Candidate,
        plan: WalkForwardPlan,
        series: Sequence[Any],
    ) -> None:
        for fold in plan.folds:
            record: EvaluationRecord = self._evaluator.evaluate(
                candidate.configuration, fold, series, fold.label
            )
            candidate.record_out_of_sample(record)

    def _top_in_sample(self, candidates: Sequence[Candidate]) -> List[Candidate]:
        """The best ``validate_top_n`` candidates by in-sample score.

        In-sample ranking is used ONLY to decide who is worth the cost of
        validation — never to decide who wins.
        """
        scored = [
            candidate
            for candidate in candidates
            if candidate.in_sample_score is not None
            and candidate.status is not CandidateStatus.REJECTED
        ]
        reverse = self._objective.direction is ObjectiveDirection.MAXIMIZE
        ordered = sorted(
            scored,
            key=lambda candidate: candidate.in_sample_score or Decimal("0"),
            reverse=reverse,
        )
        return ordered[: self._validate_top_n]

    def _remember(
        self,
        candidates: Sequence[Candidate],
        baseline: Optional[Candidate],
    ) -> None:
        if self._memory is None:
            return
        for candidate in candidates:
            self._memory.remember(candidate)
        if baseline is not None:
            self._memory.remember(baseline)
