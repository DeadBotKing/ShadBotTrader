"""Application service: orchestrate the trading decision pipeline.

Phase 14. This is the composition point that wires the domain ports
together and enforces the architectural invariants:

    strategy -> validate -> decide -> RISK GATE -> intent

The service is the only place allowed to produce a ``TradingIntent``,
and it does so exclusively for decisions that the risk gate approved.
Every step is journalled for auditability and published on the event bus.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Sequence

from ShadBotTrader.core.events.event import Event
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.events import (
    DECISION_MADE,
    INTENT_CREATED,
    RISK_REJECTED,
    SIGNAL_GENERATED,
    SIGNAL_REJECTED,
)
from ShadBotTrader.domain.strategy.ports import (
    DecisionEngine,
    DecisionJournal,
    IntentFactory,
    RiskGate,
    SignalAggregator,
    SignalValidator,
    Strategy,
)
from ShadBotTrader.domain.strategy.risk_policy import RiskVerdict
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.trading_intent import TradingIntent

_SOURCE = "TradingDecisionService"


@dataclass(frozen=True)
class TradingOutcome:
    """The full, auditable result of one evaluation cycle."""

    signals: List[TradingSignal]
    signal: Optional[TradingSignal]
    decision: Optional[TradingDecision]
    verdict: Optional[RiskVerdict]
    intent: Optional[TradingIntent]
    rejected_reason: str = ""

    @property
    def produced_intent(self) -> bool:
        return self.intent is not None


class TradingDecisionService:
    """Runs strategies through the full risk-gated decision pipeline."""

    def __init__(
        self,
        strategies: Sequence[Strategy],
        decision_engine: DecisionEngine,
        risk_gate: RiskGate,
        intent_factory: IntentFactory,
        validator: Optional[SignalValidator] = None,
        aggregator: Optional[SignalAggregator] = None,
        journal: Optional[DecisionJournal] = None,
        event_bus: Optional[EventBus] = None,
    ) -> None:
        if not strategies:
            raise ValueError("TradingDecisionService requires at least one strategy")
        if len(strategies) > 1 and aggregator is None:
            raise ValueError("Multiple strategies require a SignalAggregator")

        self._strategies = list(strategies)
        self._decision_engine = decision_engine
        self._risk_gate = risk_gate
        self._intent_factory = intent_factory
        self._validator = validator
        self._aggregator = aggregator
        self._journal = journal
        self._event_bus = event_bus

    def evaluate(self, context: StrategyContext) -> TradingOutcome:
        """Run one full decision cycle over ``context``."""
        signals = self._collect_signals(context)
        if not signals:
            return TradingOutcome(
                signals=[],
                signal=None,
                decision=None,
                verdict=None,
                intent=None,
                rejected_reason="no strategy produced a signal",
            )

        signal = self._unify(signals, context)
        if signal is None:
            return TradingOutcome(
                signals=signals,
                signal=None,
                decision=None,
                verdict=None,
                intent=None,
                rejected_reason="aggregation produced no signal",
            )

        self._publish(SIGNAL_GENERATED, self._signal_payload(signal))

        # -- validation ---------------------------------------------------
        if self._validator is not None:
            validation = self._validator.validate(signal, context)
            if not validation.approved:
                self._publish(
                    SIGNAL_REJECTED,
                    {**self._signal_payload(signal), "reason": validation.reason},
                )
                return TradingOutcome(
                    signals=signals,
                    signal=signal,
                    decision=None,
                    verdict=validation,
                    intent=None,
                    rejected_reason=validation.reason,
                )

        # -- decision -----------------------------------------------------
        decision = self._decision_engine.decide(signal, context)
        self._publish(DECISION_MADE, self._decision_payload(decision))

        if not decision.is_actionable:
            self._record(decision, None, None)
            return TradingOutcome(
                signals=signals,
                signal=signal,
                decision=decision,
                verdict=None,
                intent=None,
                rejected_reason=decision.reason,
            )

        # -- MANDATORY risk gate -------------------------------------------
        verdict = self._risk_gate.evaluate(decision, context)
        if not verdict.approved:
            self._publish(
                RISK_REJECTED,
                {**self._decision_payload(decision), "reason": verdict.reason},
            )
            self._record(decision, verdict, None)
            return TradingOutcome(
                signals=signals,
                signal=signal,
                decision=decision,
                verdict=verdict,
                intent=None,
                rejected_reason=verdict.reason,
            )

        # -- intent (only past an approving verdict) ------------------------
        intent = self._intent_factory.build(decision, context)
        if intent is not None:
            self._publish(
                INTENT_CREATED,
                {
                    "intent_id": intent.intent_id,
                    "decision_id": intent.decision_id,
                    "symbol": str(intent.symbol),
                    "intent_type": intent.intent_type.value,
                    "side": intent.side.value,
                },
            )
        self._record(decision, verdict, intent)

        return TradingOutcome(
            signals=signals,
            signal=signal,
            decision=decision,
            verdict=verdict,
            intent=intent,
            rejected_reason="" if intent is not None else "intent factory produced nothing",
        )

    def evaluate_series(self, contexts: Sequence[StrategyContext]) -> List[TradingOutcome]:
        """Evaluate many contexts in order (e.g. a backtest sweep)."""
        return [self.evaluate(context) for context in contexts]

    # -- helpers ----------------------------------------------------------
    def _collect_signals(self, context: StrategyContext) -> List[TradingSignal]:
        signals: List[TradingSignal] = []
        for strategy in self._strategies:
            signal = strategy.evaluate(context)
            if signal is not None:
                signals.append(signal)
        return signals

    def _unify(
        self,
        signals: List[TradingSignal],
        context: StrategyContext,
    ) -> Optional[TradingSignal]:
        if self._aggregator is not None:
            return self._aggregator.aggregate(signals, context)
        return signals[0]

    def _record(
        self,
        decision: TradingDecision,
        verdict: Optional[RiskVerdict],
        intent: Optional[TradingIntent],
    ) -> None:
        if self._journal is not None:
            self._journal.record(decision, verdict, intent)

    def _publish(self, event_type: str, payload: dict) -> None:
        if self._event_bus is not None:
            self._event_bus.publish(Event(event_type=event_type, payload=payload, source=_SOURCE))

    @staticmethod
    def _signal_payload(signal: TradingSignal) -> dict:
        return {
            "signal_id": signal.signal_id,
            "strategy_id": str(signal.strategy_id),
            "symbol": str(signal.symbol),
            "signal_type": signal.signal_type.value,
            "confidence": signal.confidence,
        }

    @staticmethod
    def _decision_payload(decision: TradingDecision) -> dict:
        return {
            "decision_id": decision.decision_id,
            "strategy_id": str(decision.strategy_id),
            "symbol": str(decision.symbol),
            "decision_type": decision.decision_type.value,
            "confidence": decision.confidence,
        }
