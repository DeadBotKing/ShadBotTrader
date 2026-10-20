"""Execution & Portfolio domain — Phase 14 §19-24, Phase 15.

The pipeline this package models::

    TradingIntent (risk-approved)
          |
    IntentResolver   -> ResolvedOrder    (policies become numbers)
          |
    ExecutionVenue   -> ExecutionResult  (real fills, possibly partial)
          |
    PortfolioLedger  -> PositionState    (fill-based PnL accounting)

Boundaries: Trading decides, Execution executes, Portfolio accounts.
No component crosses into another's responsibility.
"""

from ShadBotTrader.domain.execution.execution_types import (
    ExecutionRejectionReason,
    ExecutionStatus,
    IntentStatus,
    PositionSide,
    TransactionType,
)
from ShadBotTrader.domain.execution.fill import ExecutionResult, Fill
from ShadBotTrader.domain.execution.market_view import ExecutionContext, MarketQuote
from ShadBotTrader.domain.execution.money import Money
from ShadBotTrader.domain.execution.ports import (
    ExecutionJournal,
    ExecutionJournalEntry,
    ExecutionVenue,
    IntentResolver,
    PortfolioLedger,
)
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.execution.resolved_order import ResolvedOrder

__all__ = [
    "ExecutionContext",
    "ExecutionJournal",
    "ExecutionJournalEntry",
    "ExecutionRejectionReason",
    "ExecutionResult",
    "ExecutionStatus",
    "ExecutionVenue",
    "Fill",
    "IntentResolver",
    "IntentStatus",
    "MarketQuote",
    "Money",
    "PortfolioLedger",
    "PositionSide",
    "PositionState",
    "ResolvedOrder",
    "TransactionType",
]
