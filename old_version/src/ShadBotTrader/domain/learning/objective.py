"""Learning objectives (Phase 17: Learning Objective).

An objective turns a set of performance metrics into a single comparable
score. Making this explicit matters: "better" is a policy decision, not
a fact. Optimising raw return alone is what produces strategies that
blow up, so the default objective is risk-adjusted and penalises runs
with too few trades to be meaningful.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.learning.learning_types import ObjectiveDirection
from ShadBotTrader.domain.simulation.performance import PerformanceMetrics

# Scores at or below this threshold are sentinels, not measurements:
# they mean "this run carried no usable evidence". Averaging a sentinel
# with real scores would produce a meaningless number, so callers must
# treat such folds separately.
PENALTY_THRESHOLD = Decimal("-100000")


def is_penalty(score: Decimal) -> bool:
    """True when ``score`` is a sentinel rather than a real measurement."""
    return score <= PENALTY_THRESHOLD


class LearningObjective(ABC):
    """Scores a backtest result so candidates can be ranked."""

    @property
    @abstractmethod
    def name(self) -> str:
        """A stable identifier for reporting."""

    @property
    def direction(self) -> ObjectiveDirection:
        """Whether a higher score is better (the default)."""
        return ObjectiveDirection.MAXIMIZE

    @abstractmethod
    def score(self, metrics: PerformanceMetrics) -> Decimal:
        """Return the comparable score of ``metrics``."""

    def is_better(self, candidate: Decimal, incumbent: Decimal) -> bool:
        """True when ``candidate`` beats ``incumbent`` under this objective."""
        if self.direction is ObjectiveDirection.MAXIMIZE:
            return candidate > incumbent
        return candidate < incumbent


class TotalReturnObjective(LearningObjective):
    """Maximise raw return.

    Provided for comparison and explicitly NOT the default: it ignores
    risk entirely and will happily prefer a configuration that made its
    money through one enormous, unrepeatable position.
    """

    @property
    def name(self) -> str:
        return "total_return"

    def score(self, metrics: PerformanceMetrics) -> Decimal:
        return metrics.total_return


class RiskAdjustedObjective(LearningObjective):
    """Return per unit of drawdown, with a minimum activity requirement.

    score = equity_return / max(max_drawdown, floor)

    ``PerformanceMetrics.total_return`` is already the change in marked
    equity, so it already includes commissions and execution costs. The
    objective must not subtract ``total_fees`` a second time.

    A candidate with fewer than ``min_trades`` completed round trips is
    scored at a large negative value: a "perfect" result from two trades
    is noise, not evidence.
    """

    def __init__(
        self,
        min_trades: int = 5,
        drawdown_floor: Decimal = Decimal("1"),
        penalty: Decimal = Decimal("-1000000"),
    ) -> None:
        if min_trades < 0:
            raise ValidationError("min_trades must be >= 0")
        if drawdown_floor <= 0:
            raise ValidationError("drawdown_floor must be positive")
        self._min_trades = min_trades
        self._drawdown_floor = drawdown_floor
        self._penalty = penalty

    @property
    def name(self) -> str:
        return "risk_adjusted_return"

    @property
    def min_trades(self) -> int:
        return self._min_trades

    def score(self, metrics: PerformanceMetrics) -> Decimal:
        if metrics.trade_count < self._min_trades:
            return self._penalty
        drawdown = max(metrics.max_drawdown, self._drawdown_floor)
        return metrics.total_return / drawdown


class SharpeObjective(LearningObjective):
    """Maximise the Sharpe ratio.

    When Sharpe is undefined (a flat or too-short return series) the
    candidate is penalised rather than treated as zero — an undefined
    Sharpe is an absence of evidence, not a neutral result.
    """

    def __init__(self, penalty: Decimal = Decimal("-1000000")) -> None:
        self._penalty = penalty

    @property
    def name(self) -> str:
        return "sharpe"

    def score(self, metrics: PerformanceMetrics) -> Decimal:
        sharpe: Optional[Decimal] = metrics.sharpe
        return sharpe if sharpe is not None else self._penalty


class MaxDrawdownObjective(LearningObjective):
    """Minimise the worst peak-to-trough decline."""

    @property
    def name(self) -> str:
        return "max_drawdown"

    @property
    def direction(self) -> ObjectiveDirection:
        return ObjectiveDirection.MINIMIZE

    def score(self, metrics: PerformanceMetrics) -> Decimal:
        return metrics.max_drawdown
