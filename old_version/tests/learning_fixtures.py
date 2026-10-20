"""Shared builders for the self-learning tests.

Lives at the tests root so unit and integration suites can both import
it without relative-package gymnastics.
"""

from decimal import Decimal
from typing import Optional

from ShadBotTrader.domain.learning.candidate import Candidate, EvaluationRecord
from ShadBotTrader.domain.learning.parameter_space import CandidateConfiguration
from ShadBotTrader.domain.simulation.performance import PerformanceMetrics


def d(value: str) -> Decimal:
    return Decimal(value)


def make_metrics(
    total_return: str = "100",
    max_drawdown: str = "20",
    max_drawdown_percent: str = "5",
    trade_count: int = 20,
    win_count: int = 12,
    loss_count: int = 8,
    gross_profit: str = "200",
    gross_loss: str = "100",
    total_fees: str = "5",
    sharpe: Optional[str] = "0.8",
    starting_equity: str = "1000",
) -> PerformanceMetrics:
    """Performance metrics with sensible, overridable defaults."""
    start = d(starting_equity)
    ret = d(total_return)
    return PerformanceMetrics(
        starting_equity=start,
        final_equity=start + ret,
        total_return=ret,
        total_return_percent=(ret / start * d("100")) if start else d("0"),
        max_drawdown=d(max_drawdown),
        max_drawdown_percent=d(max_drawdown_percent),
        trade_count=trade_count,
        win_count=win_count,
        loss_count=loss_count,
        gross_profit=d(gross_profit),
        gross_loss=d(gross_loss),
        total_fees=d(total_fees),
        sharpe=d(sharpe) if sharpe is not None else None,
    )


def make_candidate(
    candidate_id: str = "c1",
    in_sample: Optional[str] = None,
    folds: Optional[list] = None,
    config: Optional[dict] = None,
) -> Candidate:
    """A candidate with optional in-sample and out-of-sample evidence.

    ``folds`` is a list of ``(score, metrics)`` pairs.
    """
    candidate = Candidate(
        candidate_id,
        CandidateConfiguration(config or {"lookback": 6}),
    )
    if in_sample is not None:
        candidate.record_in_sample(EvaluationRecord("in_sample", d(in_sample), make_metrics()))
    for index, (score, metrics) in enumerate(folds or [], start=1):
        candidate.record_out_of_sample(EvaluationRecord(f"fold_{index}", d(score), metrics))
    return candidate


def winning_fold(score: str = "2.0") -> tuple:
    """A fold that made money with a modest drawdown."""
    return (score, make_metrics(total_return="100", trade_count=10))


def losing_fold(score: str = "-1.0") -> tuple:
    """A fold that lost money."""
    return (score, make_metrics(total_return="-50", trade_count=10))
