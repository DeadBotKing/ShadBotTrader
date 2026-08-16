"""Signal aggregation across strategies (Phase 14, sections 28-29)."""

from __future__ import annotations

from typing import Dict, Optional, Sequence

from ShadBotTrader.domain.strategy.ports import SignalAggregator
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import SignalStrength, SignalType

_ENSEMBLE_ID = StrategyId("ensemble")


class ConfidenceWeightedAggregator(SignalAggregator):
    """Combines signals by summing confidence per direction.

    HOLD signals are ignored (they express "no opinion"). The winning
    direction is the one with the greatest total confidence; a tie yields
    HOLD rather than an arbitrary pick.
    """

    def __init__(self, min_total_confidence: float = 0.0) -> None:
        self._min_total = float(min_total_confidence)

    def aggregate(
        self,
        signals: Sequence[TradingSignal],
        context: StrategyContext,
    ) -> Optional[TradingSignal]:
        if not signals:
            return None

        actionable = [signal for signal in signals if signal.is_actionable]
        if not actionable:
            return self._hold(context, "every strategy signalled HOLD")

        totals: Dict[SignalType, float] = {}
        for signal in actionable:
            totals[signal.signal_type] = totals.get(signal.signal_type, 0.0) + signal.confidence

        best_type = max(totals, key=lambda key: totals[key])
        best_total = totals[best_type]

        # A tie between directions is not a decision.
        if sum(1 for value in totals.values() if value == best_total) > 1:
            return self._hold(context, "aggregated signals are tied")

        if best_total < self._min_total:
            return self._hold(
                context,
                f"aggregate confidence {best_total:.3f} < {self._min_total:.3f}",
            )

        contributors = [signal for signal in actionable if signal.signal_type is best_type]
        mean_confidence = sum(signal.confidence for signal in contributors) / len(contributors)

        return TradingSignal(
            signal_id=f"ensemble:{context.symbol}:{context.timeframe}:{context.timestamp}",
            strategy_id=_ENSEMBLE_ID,
            strategy_version=StrategyVersion(1),
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            signal_type=best_type,
            strength=self._strength(len(contributors), len(actionable)),
            confidence=min(mean_confidence, 1.0),
            reason=(
                f"{len(contributors)}/{len(actionable)} strategies agree on "
                f"{best_type.value} (total confidence {best_total:.3f})"
            ),
            context={
                "contributors": [str(signal.strategy_id) for signal in contributors],
                "totals": {key.value: value for key, value in totals.items()},
            },
        )

    # -- helpers ----------------------------------------------------------
    def _strength(self, agreeing: int, total: int) -> SignalStrength:
        ratio = agreeing / total if total else 0.0
        if ratio >= 1.0:
            return SignalStrength.VERY_STRONG
        if ratio >= 0.75:
            return SignalStrength.STRONG
        if ratio >= 0.5:
            return SignalStrength.NORMAL
        return SignalStrength.WEAK

    def _hold(self, context: StrategyContext, reason: str) -> TradingSignal:
        return TradingSignal(
            signal_id=f"ensemble:{context.symbol}:{context.timeframe}:{context.timestamp}",
            strategy_id=_ENSEMBLE_ID,
            strategy_version=StrategyVersion(1),
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.0,
            reason=reason,
        )
