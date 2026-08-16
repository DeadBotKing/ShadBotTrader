"""Position-aware decision engine (Phase 14, sections 17-18, 27).

Translates a validated signal into a decision by comparing the desired
direction with the position currently held. The engine never produces an
order — only a ``TradingDecision``.

Transition table (section 27)::

    position   signal    decision
    --------   ------    --------
    FLAT       BUY       ENTER
    FLAT       SELL      ENTER
    LONG       BUY       HOLD      (already aligned)
    LONG       SELL      EXIT      (reversal -> flatten first)
    SHORT      SELL      HOLD      (already aligned)
    SHORT      BUY       EXIT      (reversal -> flatten first)
    any        EXIT      EXIT / HOLD when already flat
    any        HOLD      HOLD
"""

from __future__ import annotations

from ShadBotTrader.domain.strategy.decision import TradingDecision
from ShadBotTrader.domain.strategy.ports import DecisionEngine
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_types import DecisionType, RejectionReason, SignalType


class PositionAwareDecisionEngine(DecisionEngine):
    """Decides based on the signal and the currently open position.

    ``allow_reversal`` keeps the conservative default of flattening
    before reversing: a LONG position facing a SELL signal produces EXIT,
    not an immediate REVERSE. That keeps position transitions explicit
    and auditable.
    """

    def __init__(self, allow_reversal: bool = False) -> None:
        self._allow_reversal = allow_reversal

    def decide(self, signal: TradingSignal, context: StrategyContext) -> TradingDecision:
        decision_id = f"decision:{signal.signal_id}"
        portfolio = context.portfolio

        if signal.signal_type is SignalType.HOLD:
            return TradingDecision.hold(
                decision_id,
                signal,
                reason=signal.reason or "strategy signalled HOLD",
                rejection_reason=RejectionReason.NO_SIGNAL,
            )

        is_flat = portfolio is None or portfolio.is_flat
        is_long = portfolio is not None and portfolio.is_long
        is_short = portfolio is not None and portfolio.is_short

        if signal.signal_type is SignalType.EXIT:
            if is_flat:
                return TradingDecision.hold(
                    decision_id, signal, reason="exit signal while already flat"
                )
            return self._decision(decision_id, signal, DecisionType.EXIT, "exit signal")

        if signal.signal_type is SignalType.BUY:
            if is_flat:
                return self._decision(
                    decision_id, signal, DecisionType.ENTER, "buy signal while flat"
                )
            if is_long:
                return TradingDecision.hold(
                    decision_id, signal, reason="already long; buy signal adds nothing"
                )
            # short + buy -> reversal
            return self._reversal(decision_id, signal, "buy signal while short")

        # SELL
        if is_flat:
            return self._decision(decision_id, signal, DecisionType.ENTER, "sell signal while flat")
        if is_short:
            return TradingDecision.hold(
                decision_id, signal, reason="already short; sell signal adds nothing"
            )
        return self._reversal(decision_id, signal, "sell signal while long")

    # -- helpers ----------------------------------------------------------
    def _reversal(self, decision_id: str, signal: TradingSignal, reason: str) -> TradingDecision:
        if self._allow_reversal:
            return self._decision(decision_id, signal, DecisionType.ENTER, f"{reason} (reverse)")
        return self._decision(
            decision_id, signal, DecisionType.EXIT, f"{reason} (flatten before reversing)"
        )

    def _decision(
        self,
        decision_id: str,
        signal: TradingSignal,
        decision_type: DecisionType,
        reason: str,
    ) -> TradingDecision:
        # Carry the originating signal direction forward: the intent
        # factory needs it to resolve the order side for an ENTER.
        context = dict(signal.context)
        context["signal_type"] = signal.signal_type.value
        context["signal_strength"] = signal.strength.value
        return TradingDecision(
            decision_id=decision_id,
            strategy_id=signal.strategy_id,
            strategy_version=signal.strategy_version,
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            decision_type=decision_type,
            confidence=signal.confidence,
            reason=reason,
            source_signal_id=signal.signal_id,
            context=context,
        )
