"""Console reporting for parameter searches (Phase 17: Learning Reports)."""

from __future__ import annotations

import sys
from decimal import Decimal
from typing import Optional, TextIO

from ShadBotTrader.domain.learning.candidate import Candidate
from ShadBotTrader.domain.learning.experiment import LearningExperiment
from ShadBotTrader.domain.learning.ports import OptimisationReporter


def _show(value: Optional[Decimal], digits: int = 4) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{digits}f}"


class ConsoleOptimisationReporter(OptimisationReporter):
    """Prints the search plan, per-candidate progress and the outcome."""

    def __init__(
        self,
        stream: Optional[TextIO] = None,
        show_candidates: bool = True,
    ) -> None:
        self._stream: TextIO = stream if stream is not None else sys.stdout
        self._show_candidates = show_candidates

    def _write(self, text: str = "") -> None:
        self._stream.write(text + "\n")
        self._stream.flush()

    def on_search_start(self, experiment: LearningExperiment, total: int) -> None:
        plan = experiment.plan
        self._write()
        self._write("=" * 78)
        self._write(f"  OPTIMISATION  {experiment.experiment_id}")
        self._write("=" * 78)
        self._write(f"  objective    : {experiment.objective_name}")
        self._write(f"  candidates   : {total}")
        self._write(f"  in-sample    : {plan.in_sample}")
        self._write(f"  validation   : {plan.fold_count} folds")
        for fold in plan.folds:
            self._write(f"                 {fold}")
        if experiment.hypothesis:
            self._write(f"  hypothesis   : {experiment.hypothesis}")
        self._write("-" * 78)
        if self._show_candidates:
            self._write(f"  {'#':>4} {'in-sample':>12} {'trades':>7}  configuration")
            self._write("-" * 78)

    def on_candidate_evaluated(self, candidate: Candidate, index: int, total: int) -> None:
        if not self._show_candidates:
            return
        record = candidate.in_sample
        trades = record.metrics.trade_count if record else 0
        self._write(
            f"  {index:>4} {_show(candidate.in_sample_score):>12} {trades:>7}  "
            f"{candidate.configuration.signature}"
        )

    def on_validation(self, candidate: Candidate) -> None:
        self._write(
            f"  validated {candidate.candidate_id}: "
            f"in-sample {_show(candidate.in_sample_score)} -> "
            f"out-of-sample {_show(candidate.out_of_sample_score)} "
            f"(gap {_show(candidate.overfit_gap)}, "
            f"{candidate.positive_fold_count}/{len(candidate.out_of_sample)} folds positive)"
        )

    def on_search_end(
        self,
        experiment: LearningExperiment,
        winner: Optional[Candidate],
    ) -> None:
        self._write("-" * 78)
        baseline = experiment.baseline
        if baseline is not None:
            self._write(
                f"  baseline          : out-of-sample " f"{_show(baseline.out_of_sample_score)}"
            )

        if winner is None:
            self._write("  winner            : none (no candidate survived validation)")
        else:
            self._write(f"  winner            : {winner.candidate_id}")
            self._write(f"  configuration     : {winner.configuration.signature}")
            self._write(f"  in-sample score   : {_show(winner.in_sample_score)}")
            self._write(f"  out-of-sample     : {_show(winner.out_of_sample_score)}")
            self._write(f"  overfit gap       : {_show(winner.overfit_gap)}")
            self._write(f"  status            : {winner.status.value.upper()}")
            if winner.notes:
                for note in winner.notes:
                    self._write(f"                      {note}")
        self._write("=" * 78)
        self._write()
