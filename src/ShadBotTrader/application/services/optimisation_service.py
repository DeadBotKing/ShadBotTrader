"""Application service: run a walk-forward optimisation.

Phase 17. Composition root of the Self-Learning Platform: wires a
parameter space to the Simulation Platform, applies the promotion gate
and records everything in the learning memory.

The service returns a *recommendation*. Acting on it — changing what
runs in production — is deliberately outside this platform.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping, Optional, Sequence

from ShadBotTrader.domain.learning.experiment import LearningExperiment, WalkForwardPlan
from ShadBotTrader.domain.learning.objective import (
    LearningObjective,
    RiskAdjustedObjective,
)
from ShadBotTrader.domain.learning.parameter_space import (
    CandidateConfiguration,
    ParameterSpace,
)
from ShadBotTrader.domain.learning.ports import (
    CandidateGenerator,
    OptimisationReporter,
)
from ShadBotTrader.domain.learning.promotion import PromotionGate, PromotionPolicy
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.infrastructure.learning.backtest_evaluator import (
    BacktestCandidateEvaluator,
)
from ShadBotTrader.infrastructure.learning.generators import GridSearchGenerator
from ShadBotTrader.infrastructure.learning.learning_memory import (
    InMemoryExperimentRepository,
    InMemoryLearningMemory,
)
from ShadBotTrader.infrastructure.learning.optimizer import (
    OptimisationResult,
    WalkForwardOptimizer,
)


class OptimisationService:
    """Builds and runs a complete learning experiment."""

    def __init__(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        simulation_config: Optional[SimulationConfiguration] = None,
        objective: Optional[LearningObjective] = None,
        promotion_policy: Optional[PromotionPolicy] = None,
        generator: Optional[CandidateGenerator] = None,
        validate_top_n: int = 3,
    ) -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._simulation_config = simulation_config or SimulationConfiguration()
        self._objective = objective or RiskAdjustedObjective()
        self._policy = promotion_policy or PromotionPolicy()
        self._generator = generator or GridSearchGenerator()
        self._validate_top_n = validate_top_n

        self.memory = InMemoryLearningMemory()
        self.experiments = InMemoryExperimentRepository()

    @property
    def objective(self) -> LearningObjective:
        return self._objective

    def run(
        self,
        experiment_id: str,
        parameter_values: Mapping[str, Sequence[Any]],
        candles: Sequence[Any],
        baseline: Optional[Mapping[str, Any]] = None,
        in_sample_ratio: float = 0.5,
        fold_count: int = 3,
        hypothesis: str = "",
        reporter: Optional[OptimisationReporter] = None,
    ) -> OptimisationResult:
        """Search ``parameter_values`` over ``candles`` and gate the winner."""
        if not candles:
            raise ValueError("An optimisation needs candles")

        space = ParameterSpace.from_dict(parameter_values)
        plan = WalkForwardPlan.split(
            total=len(candles),
            in_sample_ratio=in_sample_ratio,
            fold_count=fold_count,
        )

        experiment = LearningExperiment(
            experiment_id=experiment_id,
            objective_name=self._objective.name,
            plan=plan,
            hypothesis=hypothesis,
            metadata={"symbol": str(self._symbol), "space_size": space.size},
        )

        evaluator = BacktestCandidateEvaluator(
            symbol=self._symbol,
            timeframe=self._timeframe,
            objective=self._objective,
            base_configuration=self._simulation_config,
        )

        optimizer = WalkForwardOptimizer(
            generator=self._generator,
            evaluator=evaluator,
            objective=self._objective,
            gate=PromotionGate(self._policy),
            memory=self.memory,
            reporter=reporter,
            validate_top_n=self._validate_top_n,
        )

        result = optimizer.optimise(
            experiment=experiment,
            space=space,
            series=candles,
            baseline_configuration=(
                CandidateConfiguration(baseline) if baseline is not None else None
            ),
        )
        self.experiments.save(experiment)
        return result


def default_baseline() -> dict[str, Any]:
    """The incumbent configuration a candidate must beat."""
    return {
        "lookback": 6,
        "strategy_min_confidence": 0.55,
        "base_quantity": Decimal("0.01"),
    }
