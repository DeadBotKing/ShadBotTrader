"""Ports (contracts) of the trading domain — Phase 14.

These abstractions define the trading pipeline:

    Strategy -> SignalValidator -> DecisionEngine -> RiskGate -> IntentFactory

Every port lives in the domain and is implemented by infrastructure, so
the pipeline can be assembled from any combination of rule-based,
AI-driven or simulated components without the domain knowing.

Architectural invariants enforced by this design:
  * a Strategy produces signals only — never orders (section 12)
  * a TradingDecision is not an Order (section 18)
  * no intent may bypass the RiskGate (section 34)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Optional, Sequence

from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.risk_policy import RiskVerdict
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import StrategyState
from ShadBotTrader.domain.strategy.trading_intent import TradingIntent


class Strategy(ABC):
    """Turns a strategy context into trading signals.

    A strategy must be deterministic: the same context must always
    produce the same signals. It must never reach out to infrastructure,
    submit orders, or mutate the context it receives.
    """

    @property
    @abstractmethod
    def strategy_id(self) -> StrategyId:
        """The stable identity of this strategy."""

    @property
    @abstractmethod
    def version(self) -> StrategyVersion:
        """The immutable version of this strategy's logic."""

    @property
    def state(self) -> StrategyState:
        """The current lifecycle state (default: always ready)."""
        return StrategyState.READY

    @abstractmethod
    def evaluate(self, context: StrategyContext) -> Optional[TradingSignal]:
        """Evaluate ``context`` and return a signal, or None for no opinion."""


class SignalValidator(ABC):
    """Validates a signal before it can reach decision making (section 16)."""

    @abstractmethod
    def validate(self, signal: TradingSignal, context: StrategyContext) -> RiskVerdict:
        """Return an approving or rejecting verdict for ``signal``."""


class SignalAggregator(ABC):
    """Combines signals from several strategies (sections 28-29)."""

    @abstractmethod
    def aggregate(
        self,
        signals: Sequence[TradingSignal],
        context: StrategyContext,
    ) -> Optional[TradingSignal]:
        """Merge ``signals`` into one unified signal, or None."""


class DecisionEngine(ABC):
    """Turns a validated signal into a trading decision (section 17)."""

    @abstractmethod
    def decide(self, signal: TradingSignal, context: StrategyContext) -> TradingDecision:
        """Return the decision for ``signal`` (possibly HOLD)."""


class RiskGate(ABC):
    """The mandatory risk check between decision and intent (section 34).

    No implementation may be bypassed: the application pipeline must call
    the gate for every actionable decision, and must not build an intent
    when the verdict rejects.
    """

    @abstractmethod
    def evaluate(self, decision: TradingDecision, context: StrategyContext) -> RiskVerdict:
        """Return an approving or rejecting verdict for ``decision``."""


class IntentFactory(ABC):
    """Builds the execution contract from an approved decision (section 19)."""

    @abstractmethod
    def build(
        self,
        decision: TradingDecision,
        context: StrategyContext,
    ) -> Optional[TradingIntent]:
        """Return the intent for ``decision``, or None when not applicable."""


class DecisionJournal(ABC):
    """Records the audit trail of the trading pipeline (section 2).

    Every decision — including rejections — must be recordable so that a
    trading session can be reconstructed and explained afterwards.
    """

    @abstractmethod
    def record(
        self,
        decision: TradingDecision,
        verdict: Optional[RiskVerdict] = None,
        intent: Optional[TradingIntent] = None,
    ) -> None:
        """Append one decision (and its outcome) to the journal."""

    @abstractmethod
    def entries(self) -> List["JournalEntry"]:
        """Return every recorded entry in insertion order."""


class JournalEntry:
    """One recorded step of the trading pipeline."""

    def __init__(
        self,
        decision: TradingDecision,
        verdict: Optional[RiskVerdict] = None,
        intent: Optional[TradingIntent] = None,
    ) -> None:
        self._decision = decision
        self._verdict = verdict
        self._intent = intent

    @property
    def decision(self) -> TradingDecision:
        return self._decision

    @property
    def verdict(self) -> Optional[RiskVerdict]:
        return self._verdict

    @property
    def intent(self) -> Optional[TradingIntent]:
        return self._intent

    @property
    def produced_intent(self) -> bool:
        return self._intent is not None
