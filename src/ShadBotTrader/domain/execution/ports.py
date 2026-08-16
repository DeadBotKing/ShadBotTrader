"""Ports (contracts) of the execution domain — Phase 14 §19-24, Phase 15 §2.

The execution pipeline:

    TradingIntent -> IntentResolver -> ResolvedOrder
                                            |
                                      ExecutionVenue
                                            |
                                     ExecutionResult (fills)
                                            |
                                      PortfolioLedger

Boundaries these contracts protect:

* the Trading Platform never talks to a venue — it produces intents
* a venue never sees a policy — it receives a fully resolved order
* the Portfolio never guesses — it consumes real fills
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional

from ShadBotTrader.domain.execution.fill import ExecutionResult
from ShadBotTrader.domain.execution.market_view import ExecutionContext
from ShadBotTrader.domain.execution.position_state import PositionState
from ShadBotTrader.domain.execution.resolved_order import ResolvedOrder
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.strategy.trading_intent import TradingIntent


class IntentResolver(ABC):
    """Turns an approved intent's policies into a concrete order.

    Resolution needs live state (market price, equity, open position), so
    it happens in the Execution Platform rather than in Trading.
    """

    @abstractmethod
    def resolve(
        self,
        intent: TradingIntent,
        context: ExecutionContext,
    ) -> Optional[ResolvedOrder]:
        """Return the executable order, or None when it cannot be built."""


class ExecutionVenue(ABC):
    """Submits a resolved order and reports what actually happened.

    Implementations may be simulated, paper or live; the rest of the
    platform must work identically against any of them.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """A stable venue identifier, e.g. ``simulated``."""

    @abstractmethod
    def submit(self, order: ResolvedOrder, context: ExecutionContext) -> ExecutionResult:
        """Execute ``order`` and return the resulting fills."""


class PortfolioLedger(ABC):
    """Owns positions, realized PnL and the transaction history.

    The ledger is the only component allowed to mutate financial state
    (Phase 15, section 2).
    """

    @abstractmethod
    def apply(self, result: ExecutionResult) -> PositionState:
        """Fold every fill of ``result`` into the position and return it."""

    @abstractmethod
    def position(self, symbol: Symbol) -> PositionState:
        """The current position on ``symbol`` (flat when none is held)."""

    @abstractmethod
    def positions(self) -> List[PositionState]:
        """Every non-flat position."""


class ExecutionJournal(ABC):
    """Audit trail of every execution attempt, successful or not."""

    @abstractmethod
    def record(
        self,
        intent: TradingIntent,
        order: Optional[ResolvedOrder],
        result: Optional[ExecutionResult],
    ) -> None:
        """Append one execution attempt."""

    @abstractmethod
    def entries(self) -> List["ExecutionJournalEntry"]:
        """Return every recorded attempt in order."""


class ExecutionJournalEntry:
    """One recorded execution attempt."""

    def __init__(
        self,
        intent: TradingIntent,
        order: Optional[ResolvedOrder] = None,
        result: Optional[ExecutionResult] = None,
    ) -> None:
        self._intent = intent
        self._order = order
        self._result = result

    @property
    def intent(self) -> TradingIntent:
        return self._intent

    @property
    def order(self) -> Optional[ResolvedOrder]:
        return self._order

    @property
    def result(self) -> Optional[ExecutionResult]:
        return self._result

    @property
    def executed(self) -> bool:
        return self._result is not None and self._result.is_successful
