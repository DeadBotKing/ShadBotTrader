"""In-memory decision journal — the trading audit trail (Phase 14, section 2).

Every decision is recorded, including rejected ones, so a session can be
replayed and explained. The store is in-memory for now; a persistent
implementation can be swapped in behind the same port.
"""

from __future__ import annotations

from typing import List, Optional

from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.ports import DecisionJournal, JournalEntry
from ShadBotTrader.domain.strategy.risk_policy import RiskVerdict
from ShadBotTrader.domain.strategy.trading_intent import TradingIntent


class InMemoryDecisionJournal(DecisionJournal):
    """Keeps the ordered audit trail of the trading pipeline in memory."""

    def __init__(self) -> None:
        self._entries: List[JournalEntry] = []

    def record(
        self,
        decision: TradingDecision,
        verdict: Optional[RiskVerdict] = None,
        intent: Optional[TradingIntent] = None,
    ) -> None:
        self._entries.append(JournalEntry(decision=decision, verdict=verdict, intent=intent))

    def entries(self) -> List[JournalEntry]:
        return list(self._entries)

    # -- convenience queries ---------------------------------------------
    @property
    def intents(self) -> List[TradingIntent]:
        """Every intent that was actually produced."""
        return [entry.intent for entry in self._entries if entry.intent is not None]

    @property
    def rejected(self) -> List[JournalEntry]:
        """Entries whose risk verdict rejected the decision."""
        return [
            entry
            for entry in self._entries
            if entry.verdict is not None and not entry.verdict.approved
        ]

    def rejection_counts(self) -> dict[str, int]:
        """Histogram of rejection reasons, for reporting."""
        counts: dict[str, int] = {}
        for entry in self._entries:
            reason = None
            if entry.verdict is not None and entry.verdict.rejection_reason is not None:
                reason = entry.verdict.rejection_reason.value
            elif entry.decision.rejection_reason is not None:
                reason = entry.decision.rejection_reason.value
            if reason is not None:
                counts[reason] = counts.get(reason, 0) + 1
        return counts

    def clear(self) -> None:
        """Drop every recorded entry."""
        self._entries.clear()
