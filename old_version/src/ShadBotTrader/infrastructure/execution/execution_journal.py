"""In-memory execution journal — the execution audit trail."""

from __future__ import annotations

from typing import List, Optional

from ShadBotTrader.domain.execution.fill import ExecutionResult
from ShadBotTrader.domain.execution.ports import ExecutionJournal, ExecutionJournalEntry
from ShadBotTrader.domain.execution.resolved_order import ResolvedOrder
from ShadBotTrader.domain.strategy.trading_intent import TradingIntent


class InMemoryExecutionJournal(ExecutionJournal):
    """Records every execution attempt, successful or not."""

    def __init__(self) -> None:
        self._entries: List[ExecutionJournalEntry] = []

    def record(
        self,
        intent: TradingIntent,
        order: Optional[ResolvedOrder] = None,
        result: Optional[ExecutionResult] = None,
    ) -> None:
        self._entries.append(ExecutionJournalEntry(intent=intent, order=order, result=result))

    def entries(self) -> List[ExecutionJournalEntry]:
        return list(self._entries)

    # -- convenience queries -----------------------------------------------
    @property
    def executed(self) -> List[ExecutionJournalEntry]:
        """Attempts that produced at least one fill."""
        return [entry for entry in self._entries if entry.executed]

    @property
    def failed(self) -> List[ExecutionJournalEntry]:
        """Attempts that produced no fills."""
        return [entry for entry in self._entries if not entry.executed]

    def rejection_counts(self) -> dict[str, int]:
        """Histogram of execution rejection reasons."""
        counts: dict[str, int] = {}
        for entry in self._entries:
            result = entry.result
            if result is not None and result.rejection_reason is not None:
                key = result.rejection_reason.value
                counts[key] = counts.get(key, 0) + 1
        return counts

    def clear(self) -> None:
        self._entries.clear()
