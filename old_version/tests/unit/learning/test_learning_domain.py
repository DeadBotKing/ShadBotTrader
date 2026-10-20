"""Tests for the self-learning domain (Phase 17)."""

from decimal import Decimal

import pytest

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.learning.candidate import (
    best_candidate,
)
from ShadBotTrader.domain.learning.experiment import (
    DataWindow,
    LearningExperiment,
    WalkForwardPlan,
)
from ShadBotTrader.domain.learning.learning_types import (
    CandidateStatus,
    ExperimentStatus,
    ObjectiveDirection,
    RejectionReason,
    ValidationOutcome,
)
from ShadBotTrader.domain.learning.objective import (
    MaxDrawdownObjective,
    RiskAdjustedObjective,
    SharpeObjective,
    TotalReturnObjective,
)
from ShadBotTrader.domain.learning.parameter_space import (
    CandidateConfiguration,
    ParameterGrid,
    ParameterSpace,
)
from ShadBotTrader.domain.learning.promotion import (
    PromotionGate,
    PromotionPolicy,
    PromotionVerdict,
)
from tests.learning_fixtures import (
    d,
    losing_fold,
    make_candidate,
    make_metrics,
    winning_fold,
)


# ------------------------------------------------------- parameter space ---
class TestParameterSpace:
    def test_grid_rejects_empty_values(self):
        with pytest.raises(ValidationError, match="at least one value"):
            ParameterGrid("lookback", [])

    def test_rejects_duplicate_parameter_names(self):
        with pytest.raises(ValidationError, match="Duplicate parameter"):
            ParameterSpace([ParameterGrid("a", [1]), ParameterGrid("a", [2])])

    def test_size_is_the_cartesian_product(self):
        space = ParameterSpace.from_dict({"a": [1, 2, 3], "b": [10, 20]})
        assert space.size == 6

    def test_grid_enumeration_is_complete_and_deterministic(self):
        space = ParameterSpace.from_dict({"a": [1, 2], "b": [10, 20]})
        first = [c.signature for c in space.grid_configurations()]
        second = [c.signature for c in space.grid_configurations()]
        assert len(first) == 4
        assert first == second  # same order every time

    def test_random_search_is_reproducible_for_a_seed(self):
        space = ParameterSpace.from_dict({"a": list(range(10)), "b": list(range(10))})
        first = [c.signature for c in space.random_configurations(5, seed=7)]
        second = [c.signature for c in space.random_configurations(5, seed=7)]
        third = [c.signature for c in space.random_configurations(5, seed=99)]
        assert first == second
        assert first != third

    def test_random_search_returns_distinct_configurations(self):
        space = ParameterSpace.from_dict({"a": [1, 2, 3], "b": [4, 5, 6]})
        picked = space.random_configurations(9, seed=1)
        assert len({c.signature for c in picked}) == len(picked)

    def test_random_search_cannot_exceed_the_space(self):
        """A tiny space must not loop forever trying to fill a big request."""
        space = ParameterSpace.from_dict({"a": [1, 2]})
        assert len(space.random_configurations(50, seed=1)) == 2

    def test_configuration_signature_is_order_independent(self):
        first = CandidateConfiguration({"a": 1, "b": 2})
        second = CandidateConfiguration({"b": 2, "a": 1})
        assert first.signature == second.signature
        assert first == second

    def test_configuration_reads_decimals_exactly(self):
        config = CandidateConfiguration({"size": "0.1"})
        assert config.decimal("size") == Decimal("0.1")


# ------------------------------------------------------------ objectives ---
class TestObjectives:
    def test_total_return_ignores_risk(self):
        objective = TotalReturnObjective()
        assert objective.score(make_metrics(total_return="250")) == d("250")

    def test_risk_adjusted_uses_equity_return_once(self):
        """Equity return already includes fees; they must not be subtracted twice."""
        objective = RiskAdjustedObjective(min_trades=1)
        metrics = make_metrics(total_return="200", max_drawdown="20", total_fees="10")
        assert objective.score(metrics) == d("10")

    def test_risk_adjusted_penalises_too_few_trades(self):
        """A great result from 2 trades is noise, not evidence."""
        objective = RiskAdjustedObjective(min_trades=10)
        thin = make_metrics(total_return="1000", trade_count=2)
        assert objective.score(thin) < d("-1000")

    def test_drawdown_floor_prevents_division_blowup(self):
        objective = RiskAdjustedObjective(min_trades=1, drawdown_floor=d("1"))
        flat = make_metrics(total_return="50", max_drawdown="0", total_fees="0")
        assert objective.score(flat) == d("50")

    def test_sharpe_objective_penalises_undefined_sharpe(self):
        objective = SharpeObjective()
        assert objective.score(make_metrics(sharpe="1.5")) == d("1.5")
        assert objective.score(make_metrics(sharpe=None)) < d("-1000")

    def test_drawdown_objective_is_minimised(self):
        objective = MaxDrawdownObjective()
        assert objective.direction is ObjectiveDirection.MINIMIZE
        assert objective.is_better(d("10"), d("20"))  # smaller is better
        assert not objective.is_better(d("30"), d("20"))

    def test_maximising_objective_comparison(self):
        assert TotalReturnObjective().is_better(d("10"), d("5"))


# ------------------------------------------------------------- candidate ---
class TestCandidate:
    def test_out_of_sample_score_is_the_mean_of_folds(self):
        candidate = make_candidate(folds=[winning_fold("3"), winning_fold("1")])
        assert candidate.out_of_sample_score == d("2")

    def test_worst_fold_is_tracked(self):
        candidate = make_candidate(folds=[winning_fold("3"), losing_fold("-2")])
        assert candidate.worst_fold_score == d("-2")

    def test_overfit_gap_exposes_memorisation(self):
        """High in-sample, low out-of-sample is the classic signature."""
        candidate = make_candidate(in_sample="10", folds=[winning_fold("1")])
        assert candidate.overfit_gap == d("9")

    def test_overfit_gap_is_none_without_both_sides(self):
        assert make_candidate(in_sample="5").overfit_gap is None
        assert make_candidate(folds=[winning_fold()]).overfit_gap is None

    def test_positive_fold_count(self):
        candidate = make_candidate(folds=[winning_fold(), losing_fold(), winning_fold()])
        assert candidate.positive_fold_count == 2

    def test_cannot_promote_without_validation(self):
        """The structural guard against pushing an untested candidate."""
        candidate = make_candidate(in_sample="5")
        assert candidate.status is CandidateStatus.EVALUATED
        with pytest.raises(ValidationError, match="must pass validation first"):
            candidate.promote()

    def test_promotion_requires_the_validated_state(self):
        candidate = make_candidate(in_sample="5", folds=[winning_fold()])
        candidate.validate(ValidationOutcome.PASSED)
        candidate.promote()
        assert candidate.status is CandidateStatus.PROMOTED

    def test_rejected_candidate_cannot_be_promoted(self):
        candidate = make_candidate(in_sample="5", folds=[winning_fold()])
        candidate.reject(RejectionReason.NEGATIVE_RETURN)
        with pytest.raises(ValidationError):
            candidate.promote()

    def test_rejection_records_a_machine_readable_reason(self):
        candidate = make_candidate()
        candidate.reject(RejectionReason.EXCESSIVE_DRAWDOWN, "too deep")
        assert candidate.status is CandidateStatus.REJECTED
        assert candidate.rejection_reason is RejectionReason.EXCESSIVE_DRAWDOWN
        assert "too deep" in candidate.notes

    def test_best_candidate_ranks_on_out_of_sample(self):
        """Ranking must ignore in-sample scores entirely."""
        overfit = make_candidate("overfit", in_sample="100", folds=[losing_fold("-5")])
        honest = make_candidate("honest", in_sample="2", folds=[winning_fold("3")])
        assert best_candidate([overfit, honest]) is honest

    def test_best_candidate_skips_unvalidated_and_rejected(self):
        unvalidated = make_candidate("u", in_sample="100")
        rejected = make_candidate("r", folds=[winning_fold("9")])
        rejected.reject(RejectionReason.OVERFIT_SUSPECTED)
        good = make_candidate("g", folds=[winning_fold("1")])
        assert best_candidate([unvalidated, rejected, good]) is good

    def test_best_candidate_returns_none_without_evidence(self):
        assert best_candidate([make_candidate("a", in_sample="5")]) is None


# -------------------------------------------------------- walk-forward ---
class TestWalkForwardPlan:
    def test_split_produces_disjoint_windows(self):
        plan = WalkForwardPlan.split(total=100, in_sample_ratio=0.5, fold_count=2)
        assert plan.in_sample.start == 0
        assert plan.in_sample.end == 50
        assert [(f.start, f.end) for f in plan.folds] == [(50, 75), (75, 100)]

    def test_last_fold_absorbs_the_remainder(self):
        """No data is silently discarded."""
        plan = WalkForwardPlan.split(total=100, in_sample_ratio=0.5, fold_count=3)
        assert plan.folds[-1].end == 100

    def test_folds_may_not_overlap_the_training_window(self):
        """Overlap would leak training data into validation."""
        in_sample = DataWindow("in_sample", 0, 50)
        leaking = DataWindow("fold_1", 40, 80)
        with pytest.raises(ValidationError, match="leak training data"):
            WalkForwardPlan(in_sample, [leaking])

    def test_plan_needs_at_least_one_fold(self):
        with pytest.raises(ValidationError, match="at least one validation fold"):
            WalkForwardPlan(DataWindow("in_sample", 0, 10), [])

    def test_split_rejects_impossible_requests(self):
        with pytest.raises(ValidationError):
            WalkForwardPlan.split(total=4, in_sample_ratio=0.5, fold_count=10)
        with pytest.raises(ValidationError):
            WalkForwardPlan.split(total=100, in_sample_ratio=1.5)

    def test_window_slices_a_series(self):
        window = DataWindow("w", 2, 5)
        assert window.slice(list(range(10))) == [2, 3, 4]
        assert window.size == 3

    def test_window_must_be_non_empty(self):
        with pytest.raises(ValidationError, match="non-empty"):
            DataWindow("w", 5, 5)


class TestLearningExperiment:
    def _experiment(self) -> LearningExperiment:
        return LearningExperiment(
            experiment_id="e1",
            objective_name="risk_adjusted_return",
            plan=WalkForwardPlan.split(100, 0.5, 2),
        )

    def test_lifecycle(self):
        experiment = self._experiment()
        assert experiment.status is ExperimentStatus.CREATED
        experiment.start()
        experiment.complete()
        assert experiment.status is ExperimentStatus.COMPLETED

    def test_cannot_complete_before_starting(self):
        with pytest.raises(ValidationError):
            self._experiment().complete()

    def test_failure_records_a_reason(self):
        experiment = self._experiment()
        experiment.start()
        experiment.fail("evaluator crashed")
        assert experiment.status is ExperimentStatus.FAILED
        assert experiment.failure_reason == "evaluator crashed"


# --------------------------------------------------------- promotion gate ---
class TestPromotionGate:
    def _policy(self, **overrides) -> PromotionPolicy:
        defaults = dict(
            min_out_of_sample_trades=10,
            min_validation_folds=2,
            max_drawdown_percent=d("25"),
            require_positive_return=True,
            min_positive_fold_ratio=d("0.5"),
        )
        defaults.update(overrides)
        return PromotionPolicy(**defaults)

    def test_approves_a_genuinely_better_candidate(self):
        gate = PromotionGate(self._policy())
        candidate = make_candidate(in_sample="2", folds=[winning_fold("3"), winning_fold("2")])
        verdict = gate.evaluate(candidate, baseline_score=d("1"))
        assert verdict.approved

    def test_rejects_when_it_does_not_beat_the_baseline(self):
        gate = PromotionGate(self._policy())
        candidate = make_candidate(folds=[winning_fold("1"), winning_fold("1")])
        verdict = gate.evaluate(candidate, baseline_score=d("5"))
        assert not verdict.approved
        assert verdict.rejection_reason is RejectionReason.WORSE_THAN_BASELINE

    def test_rejects_too_few_validation_folds(self):
        gate = PromotionGate(self._policy(min_validation_folds=3))
        candidate = make_candidate(folds=[winning_fold(), winning_fold()])
        verdict = gate.evaluate(candidate)
        assert verdict.rejection_reason is RejectionReason.FAILED_VALIDATION_FOLD

    def test_rejects_too_few_trades(self):
        """A result built on 3 trades is not evidence."""
        gate = PromotionGate(self._policy(min_out_of_sample_trades=100))
        candidate = make_candidate(folds=[winning_fold(), winning_fold()])
        verdict = gate.evaluate(candidate)
        assert verdict.rejection_reason is RejectionReason.INSUFFICIENT_TRADES

    def test_rejects_excessive_drawdown(self):
        gate = PromotionGate(self._policy(max_drawdown_percent=d("5")))
        deep = ("2", make_metrics(total_return="100", max_drawdown_percent="40", trade_count=10))
        candidate = make_candidate(folds=[deep, winning_fold()])
        verdict = gate.evaluate(candidate)
        assert verdict.rejection_reason is RejectionReason.EXCESSIVE_DRAWDOWN

    def test_rejects_negative_aggregate_return(self):
        gate = PromotionGate(self._policy())
        candidate = make_candidate(folds=[losing_fold("-1"), losing_fold("-2")])
        verdict = gate.evaluate(candidate)
        assert verdict.rejection_reason is RejectionReason.NEGATIVE_RETURN

    def test_rejects_a_single_lucky_fold(self):
        """One huge win among losses is not a strategy."""
        gate = PromotionGate(self._policy(min_positive_fold_ratio=d("0.75")))
        lucky = ("10", make_metrics(total_return="900", trade_count=10))
        candidate = make_candidate(folds=[lucky, losing_fold(), losing_fold()])
        verdict = gate.evaluate(candidate)
        assert verdict.rejection_reason is RejectionReason.UNSTABLE_OUT_OF_SAMPLE

    def test_rejects_a_suspicious_overfit_gap(self):
        gate = PromotionGate(self._policy(max_overfit_gap=d("1")))
        candidate = make_candidate(in_sample="50", folds=[winning_fold("2"), winning_fold("2")])
        verdict = gate.evaluate(candidate)
        assert verdict.rejection_reason is RejectionReason.OVERFIT_SUSPECTED

    def test_verdict_requires_a_reason_when_rejecting(self):
        with pytest.raises(ValidationError):
            PromotionVerdict(approved=False)

    def test_verdict_is_falsy_when_rejected(self):
        assert PromotionVerdict.approve()
        assert not PromotionVerdict.reject(RejectionReason.NEGATIVE_RETURN)

    def test_policy_validates_its_own_bounds(self):
        with pytest.raises(ValidationError):
            PromotionPolicy(min_positive_fold_ratio=d("2"))
        with pytest.raises(ValidationError):
            PromotionPolicy(min_validation_folds=0)


class TestPenaltySentinels:
    """Regression guards: a penalty marker is not a score.

    ``RiskAdjustedObjective`` returns -1,000,000 for a run with too few
    trades to judge. Averaging that with real fold scores produced
    figures like -333,333 — arithmetically correct and completely
    meaningless. A sentinel must propagate, not dilute.
    """

    def test_a_penalised_fold_is_not_averaged_away(self):
        penalty = ("-1000000", make_metrics(trade_count=1))
        candidate = make_candidate(folds=[penalty, winning_fold("2"), winning_fold("2")])

        assert candidate.has_penalised_folds
        assert candidate.penalised_fold_count == 1
        # the score stays at the sentinel level instead of becoming ~-333333
        assert candidate.out_of_sample_score == d("-1000000")

    def test_clean_folds_are_still_averaged(self):
        candidate = make_candidate(folds=[winning_fold("3"), winning_fold("1")])
        assert not candidate.has_penalised_folds
        assert candidate.out_of_sample_score == d("2")

    def test_overfit_gap_is_undefined_against_a_sentinel(self):
        """The difference between a score and a marker measures nothing."""
        penalty = ("-1000000", make_metrics(trade_count=1))
        candidate = make_candidate(in_sample="2", folds=[penalty])
        assert candidate.overfit_gap is None

    def test_gate_rejects_a_candidate_with_an_unusable_fold(self):
        penalty = ("-1000000", make_metrics(trade_count=1))
        candidate = make_candidate(
            in_sample="5", folds=[penalty, winning_fold("3"), winning_fold("3")]
        )
        gate = PromotionGate(PromotionPolicy(min_out_of_sample_trades=1, min_validation_folds=2))
        verdict = gate.evaluate(candidate)

        assert not verdict.approved
        assert verdict.rejection_reason is RejectionReason.INSUFFICIENT_TRADES
        assert "too little activity" in verdict.reason

    def test_is_penalty_boundary(self):
        from ShadBotTrader.domain.learning.objective import is_penalty

        assert is_penalty(d("-1000000"))
        assert not is_penalty(d("-5"))
        assert not is_penalty(d("0"))
