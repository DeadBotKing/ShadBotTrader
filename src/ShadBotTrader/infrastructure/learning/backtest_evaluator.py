"""Evaluates candidates by running real backtests (Phase 17 + Phase 16).

Self-learning never simulates anything itself: it hands a configuration
and a data window to the Simulation Platform and reads the metrics back.
That keeps a single source of truth for "how did this perform".

Tunable parameters understood by this evaluator:

    base_quantity          order size
    strategy_min_confidence  confidence a signal needs to act
    lookback               momentum lookback in bars
    warmup_bars            bars skipped before trading starts
    max_open_positions     risk limit
    min_confidence         risk-gate confidence floor
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Sequence

from ShadBotTrader.application.services.backtest_service import BacktestService
from ShadBotTrader.domain.learning.candidate import EvaluationRecord
from ShadBotTrader.domain.learning.experiment import DataWindow
from ShadBotTrader.domain.learning.objective import LearningObjective
from ShadBotTrader.domain.learning.parameter_space import CandidateConfiguration
from ShadBotTrader.domain.learning.ports import CandidateEvaluator
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.session import SimulationConfiguration
from ShadBotTrader.domain.strategy.risk_policy import RiskPolicy
from ShadBotTrader.infrastructure.simulation import MomentumPredictionSource


class BacktestCandidateEvaluator(CandidateEvaluator):
    """Scores a configuration by backtesting it over a data window."""

    def __init__(
        self,
        symbol: Symbol,
        timeframe: Timeframe,
        objective: LearningObjective,
        base_configuration: SimulationConfiguration | None = None,
    ) -> None:
        self._symbol = symbol
        self._timeframe = timeframe
        self._objective = objective
        self._base = base_configuration or SimulationConfiguration()

    @property
    def objective(self) -> LearningObjective:
        return self._objective

    def evaluate(
        self,
        configuration: CandidateConfiguration,
        window: DataWindow,
        series: Sequence[Any],
        label: str,
    ) -> EvaluationRecord:
        candles = window.slice(series)
        if not candles:
            raise ValueError(f"Window {window} produced no candles")

        base = self._base
        simulation_config = SimulationConfiguration(
            initial_capital=base.initial_capital,
            base_currency=base.base_currency,
            spread=base.spread,
            slippage_rate=base.slippage_rate,
            commission_rate=base.commission_rate,
            seed=base.seed,
            mode=base.mode,
            warmup_bars=int(configuration.get("warmup_bars", base.warmup_bars)),
        )

        service = BacktestService(
            configuration=simulation_config,
            risk_policy=RiskPolicy(
                max_open_positions=int(configuration.get("max_open_positions", 3)),
                min_confidence=float(configuration.get("min_confidence", 0.5)),
            ),
            base_quantity=configuration.decimal("base_quantity", "0.01"),
            strategy_min_confidence=float(configuration.get("strategy_min_confidence", 0.55)),
        )

        result = service.run(
            f"{label}:{configuration.signature}",
            self._symbol,
            self._timeframe,
            candles,
            prediction_source=MomentumPredictionSource(
                lookback=int(configuration.get("lookback", 6))
            ),
        )

        return EvaluationRecord(
            label=label,
            score=self._objective.score(result.metrics),
            metrics=result.metrics,
            bars=result.bars_processed,
        )


def default_parameter_values() -> dict[str, list[Any]]:
    """A reasonable starting grid for the momentum strategy.

    Deliberately small: a search space should be defensible, not
    exhaustive. Every value here changes behaviour in a way a human can
    explain.
    """
    return {
        "lookback": [3, 6, 12],
        "strategy_min_confidence": [0.55, 0.65, 0.75],
        "base_quantity": [Decimal("0.01"), Decimal("0.02")],
    }
