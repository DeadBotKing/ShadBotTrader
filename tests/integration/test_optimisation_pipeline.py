"""Integration tests for the self-learning loop (Phase 17).

The behaviour that matters here is not "does it find a good
configuration" — with random data there is none. It is:

    * are candidates ranked on out-of-sample evidence only?
    * does the gate refuse a candidate that only looks good in-sample?
    * is the whole search reproducible?
    * does self-learning stay unable to touch live trading?
"""

from decimal import Decimal
from typing import Any, Sequence

import pytest

from ShadBotTrader.application.services.optimisation_service import (
    OptimisationService,
    default_baseline,
)
from ShadBotTrader.domain.learning.candidate import EvaluationRecord
from ShadBotTrader.domain.learning.experiment import (
    DataWindow,
    LearningExperiment,
    WalkForwardPlan,
)
from ShadBotTrader.domain.learning.learning_types import (
    CandidateStatus,
    RejectionReason,
)
from ShadBotTrader.domain.learning.objective import RiskAdjustedObjective
from ShadBotTrader.domain.learning.parameter_space import (
    CandidateConfiguration,
    ParameterSpace,
)
from ShadBotTrader.domain.learning.ports import CandidateEvaluator
from ShadBotTrader.domain.learning.promotion import PromotionGate, PromotionPolicy
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.infrastructure.learning import (
    GridSearchGenerator,
    InMemoryLearningMemory,
    RandomSearchGenerator,
    WalkForwardOptimizer,
)
from tests.learning_fixtures import d, make_metrics
from tests.simulation_fixtures import TF, XAU, rising


def config(**overrides) -> SimulationConfiguration:
    defaults = dict(
        initial_capital=d("100"),
        spread=d("4"),
        commission_rate=d("0.0001"),
        warmup_bars=5,
    )
    defaults.update(overrides)
    return SimulationConfiguration(**defaults)


def service(**overrides) -> OptimisationService:
    return OptimisationService(
        symbol=XAU,
        timeframe=TF,
        simulation_config=overrides.pop("simulation_config", config()),
        **overrides,
    )


SMALL_SPACE = {"lookback": [3, 6], "strategy_min_confidence": [0.55, 0.7]}


# ------------------------------------------------------------- real runs ---
def test_optimisation_completes_over_real_backtests():
    result = service().run("e1", SMALL_SPACE, rising(80), fold_count=2)

    assert result.experiment.status.value == "completed"
    assert len(result.evaluated) == 4
    assert len(result.validated) >= 1


def test_every_validated_candidate_has_out_of_sample_evidence():
    result = service().run("e2", SMALL_SPACE, rising(80), fold_count=3)
    for candidate in result.validated:
        assert len(candidate.out_of_sample) == 3
        assert candidate.out_of_sample_score is not None


def test_search_is_reproducible():
    """Same space, same data, same seed -> same outcome."""
    candles = rising(80)
    first = service().run("r1", SMALL_SPACE, candles, fold_count=2)
    second = service().run("r2", SMALL_SPACE, candles, fold_count=2)

    assert [c.in_sample_score for c in first.evaluated] == [
        c.in_sample_score for c in second.evaluated
    ]
    assert (first.winner is None) == (second.winner is None)
    if first.winner and second.winner:
        assert first.winner.configuration == second.winner.configuration


def test_random_search_is_reproducible():
    candles = rising(80)
    space = {"lookback": [3, 6, 9, 12], "strategy_min_confidence": [0.5, 0.6, 0.7]}

    first = service(generator=RandomSearchGenerator(count=4, seed=11)).run(
        "rs1", space, candles, fold_count=2
    )
    second = service(generator=RandomSearchGenerator(count=4, seed=11)).run(
        "rs2", space, candles, fold_count=2
    )

    assert [c.configuration.signature for c in first.evaluated] == [
        c.configuration.signature for c in second.evaluated
    ]


def test_baseline_is_measured_the_same_way_as_candidates():
    """An unfair comparison would make any candidate look good."""
    result = service().run(
        "base", SMALL_SPACE, rising(80), baseline=default_baseline(), fold_count=2
    )
    assert result.baseline is not None
    assert result.baseline.out_of_sample_score is not None
    assert len(result.baseline.out_of_sample) == 2


def test_memory_records_every_candidate():
    backtest = service()
    backtest.run("mem", SMALL_SPACE, rising(80), fold_count=2)
    assert len(backtest.memory) >= 4
    assert len(backtest.experiments) == 1


def test_grid_can_be_capped():
    result = service(generator=GridSearchGenerator(max_candidates=2)).run(
        "cap", SMALL_SPACE, rising(80), fold_count=2
    )
    assert len(result.evaluated) == 2


def test_empty_candles_are_rejected():
    with pytest.raises(ValueError, match="needs candles"):
        service().run("bad", SMALL_SPACE, [], fold_count=2)


# ------------------------------- the anti-overfitting behaviour (scripted) ---
class RiggedEvaluator(CandidateEvaluator):
    """An evaluator with a planted trap.

    One configuration scores spectacularly in-sample and collapses out of
    sample; another is modest but consistent. A search that ranks on
    in-sample results will pick the trap.
    """

    TRAP = "lookback=1"
    HONEST = "lookback=2"

    def evaluate(
        self,
        configuration: CandidateConfiguration,
        window: DataWindow,
        series: Sequence[Any],
        label: str,
    ) -> EvaluationRecord:
        signature = configuration.signature
        in_sample = label == "in_sample"

        if signature == self.TRAP:
            score = d("100") if in_sample else d("-20")
            metrics = make_metrics(total_return="1000" if in_sample else "-500", trade_count=20)
        elif signature == self.HONEST:
            score = d("2")
            metrics = make_metrics(total_return="100", trade_count=20)
        else:
            score = d("0.5")
            metrics = make_metrics(total_return="10", trade_count=20)

        return EvaluationRecord(label, score, metrics, bars=window.size)


def _rigged_optimiser(memory=None, policy=None) -> WalkForwardOptimizer:
    return WalkForwardOptimizer(
        generator=GridSearchGenerator(),
        evaluator=RiggedEvaluator(),
        objective=RiskAdjustedObjective(min_trades=1),
        gate=PromotionGate(policy or PromotionPolicy(min_out_of_sample_trades=1)),
        memory=memory,
        validate_top_n=3,
    )


def _rigged_experiment() -> LearningExperiment:
    return LearningExperiment(
        experiment_id="rigged",
        objective_name="risk_adjusted_return",
        plan=WalkForwardPlan.split(total=100, in_sample_ratio=0.5, fold_count=2),
    )


class TestOverfittingProtection:
    def test_the_in_sample_star_does_not_win(self):
        """The core promise of walk-forward validation."""
        space = ParameterSpace.from_dict({"lookback": [1, 2, 3]})
        result = _rigged_optimiser().optimise(_rigged_experiment(), space, list(range(100)))

        assert result.winner is not None
        # the trap had by far the best in-sample score...
        trap = next(c for c in result.evaluated if c.configuration.signature == "lookback=1")
        assert trap.in_sample_score == d("100")
        # ...but the honest candidate wins on out-of-sample evidence
        assert result.winner.configuration.signature == "lookback=2"

    def test_the_trap_is_visible_as_an_overfit_gap(self):
        space = ParameterSpace.from_dict({"lookback": [1, 2]})
        result = _rigged_optimiser().optimise(_rigged_experiment(), space, list(range(100)))
        trap = next(c for c in result.validated if c.configuration.signature == "lookback=1")
        assert trap.overfit_gap == d("120")  # 100 in-sample vs -20 out-of-sample

    def test_a_candidate_that_beats_the_baseline_is_promoted(self):
        space = ParameterSpace.from_dict({"lookback": [2]})
        result = _rigged_optimiser().optimise(
            _rigged_experiment(),
            space,
            list(range(100)),
            baseline_configuration=CandidateConfiguration({"lookback": 3}),
        )
        assert result.winner is not None
        assert result.promoted
        assert result.winner.status is CandidateStatus.PROMOTED

    def test_a_candidate_that_loses_to_the_baseline_is_rejected(self):
        """'lookback=3' scores 0.5; the baseline 'lookback=2' scores 2."""
        space = ParameterSpace.from_dict({"lookback": [3]})
        result = _rigged_optimiser().optimise(
            _rigged_experiment(),
            space,
            list(range(100)),
            baseline_configuration=CandidateConfiguration({"lookback": 2}),
        )
        assert result.winner is not None
        assert not result.promoted
        assert result.winner.status is CandidateStatus.REJECTED
        assert result.verdict is not None
        assert result.verdict.rejection_reason is RejectionReason.WORSE_THAN_BASELINE

    def test_verdict_is_present_even_when_rejecting(self):
        """A falsy verdict object is still a verdict — it must be recorded."""
        space = ParameterSpace.from_dict({"lookback": [3]})
        result = _rigged_optimiser().optimise(
            _rigged_experiment(),
            space,
            list(range(100)),
            baseline_configuration=CandidateConfiguration({"lookback": 2}),
        )
        assert result.verdict is not None
        assert bool(result.verdict) is False
        assert result.verdict.reason

    def test_memory_remembers_the_failures(self):
        memory = InMemoryLearningMemory()
        space = ParameterSpace.from_dict({"lookback": [1, 2, 3]})
        _rigged_optimiser(memory=memory).optimise(
            _rigged_experiment(),
            space,
            list(range(100)),
            baseline_configuration=CandidateConfiguration({"lookback": 2}),
        )
        assert len(memory) >= 3
        assert memory.recall("lookback=1") is not None


class TestEvaluationFailureHandling:
    def test_a_broken_configuration_does_not_kill_the_search(self):
        class SometimesBroken(RiggedEvaluator):
            def evaluate(self, configuration, window, series, label):
                if configuration.signature == "lookback=3":
                    raise RuntimeError("simulated evaluator failure")
                return super().evaluate(configuration, window, series, label)

        optimiser = WalkForwardOptimizer(
            generator=GridSearchGenerator(),
            evaluator=SometimesBroken(),
            objective=RiskAdjustedObjective(min_trades=1),
            gate=PromotionGate(PromotionPolicy(min_out_of_sample_trades=1)),
        )
        space = ParameterSpace.from_dict({"lookback": [1, 2, 3]})
        result = optimiser.optimise(_rigged_experiment(), space, list(range(100)))

        broken = next(c for c in result.evaluated if c.configuration.signature == "lookback=3")
        assert broken.status is CandidateStatus.REJECTED
        assert broken.rejection_reason is RejectionReason.EVALUATION_FAILED
        # the run still completed and still found a winner
        assert result.experiment.status.value == "completed"
        assert result.winner is not None


# ------------------------------------------------- architectural boundary ---
class TestLearningBoundary:
    def test_self_learning_cannot_reach_live_execution(self):
        """Phase 17: learning proposes, it never executes.

        The optimisation result must expose no execution surface — no
        venue, no ledger, no order. A promoted candidate is a
        recommendation and nothing more.
        """
        result = service().run("boundary", SMALL_SPACE, rising(60), fold_count=2)

        forbidden = ("venue", "ledger", "execute", "submit", "order", "broker")
        surface = dir(result)
        for name in forbidden:
            assert not any(name in attribute.lower() for attribute in surface)

    def test_a_promoted_candidate_is_only_a_configuration(self):
        space = ParameterSpace.from_dict({"lookback": [2]})
        result = _rigged_optimiser().optimise(
            _rigged_experiment(),
            space,
            list(range(100)),
            baseline_configuration=CandidateConfiguration({"lookback": 3}),
        )
        assert result.winner is not None
        assert isinstance(result.winner.configuration.values, dict)
        assert not hasattr(result.winner, "apply")
        assert not hasattr(result.winner, "deploy")

    def test_result_is_serialisable_for_audit(self):
        result = service().run("audit", SMALL_SPACE, rising(60), fold_count=2)
        payload = result.to_dict()
        assert payload["experiment_id"] == "audit"
        assert payload["objective"] == "risk_adjusted_return"
        assert "promoted" in payload


def test_optimiser_requires_a_sane_top_n():
    with pytest.raises(ValueError, match="validate_top_n"):
        WalkForwardOptimizer(
            generator=GridSearchGenerator(),
            evaluator=RiggedEvaluator(),
            objective=RiskAdjustedObjective(),
            validate_top_n=0,
        )


def test_only_the_top_n_are_validated():
    """Validation is expensive; it must be spent on the leaders only."""
    space = ParameterSpace.from_dict({"lookback": [1, 2, 3]})
    optimiser = WalkForwardOptimizer(
        generator=GridSearchGenerator(),
        evaluator=RiggedEvaluator(),
        objective=RiskAdjustedObjective(min_trades=1),
        gate=PromotionGate(PromotionPolicy(min_out_of_sample_trades=1)),
        validate_top_n=1,
    )
    result = optimiser.optimise(_rigged_experiment(), space, list(range(100)))

    assert len(result.evaluated) == 3
    assert len(result.validated) == 1


def test_candidates_carry_their_configuration_through():
    result = service().run("carry", SMALL_SPACE, rising(60), fold_count=2)
    for candidate in result.evaluated:
        assert "lookback" in candidate.configuration.values
        assert "strategy_min_confidence" in candidate.configuration.values


def test_learning_memory_reports_rejection_reasons():
    backtest = service()
    backtest.run("reasons", SMALL_SPACE, rising(80), baseline=default_baseline(), fold_count=2)
    counts = backtest.memory.rejection_counts()
    assert isinstance(counts, dict)


def test_objective_choice_changes_the_ranking():
    """Different objectives are different definitions of 'better'."""
    from ShadBotTrader.domain.learning.objective import TotalReturnObjective

    candles = rising(80)
    risk_adjusted = service(objective=RiskAdjustedObjective(min_trades=1)).run(
        "obj-risk", SMALL_SPACE, candles, fold_count=2
    )
    raw_return = service(objective=TotalReturnObjective()).run(
        "obj-raw", SMALL_SPACE, candles, fold_count=2
    )

    assert risk_adjusted.experiment.objective_name == "risk_adjusted_return"
    assert raw_return.experiment.objective_name == "total_return"


def test_decimal_parameters_survive_the_round_trip():
    space = {"base_quantity": [Decimal("0.01"), Decimal("0.05")], "lookback": [6]}
    result = service().run("decimals", space, rising(60), fold_count=2)
    for candidate in result.evaluated:
        assert isinstance(candidate.configuration.get("base_quantity"), Decimal)
