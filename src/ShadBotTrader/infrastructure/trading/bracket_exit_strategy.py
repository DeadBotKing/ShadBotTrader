"""Strategy used by the simulator to close a bracketed position.

A bracket trigger is an application-level market event, not a new model
prediction.  Routing it through a tiny strategy keeps the normal
strategy -> decision -> risk gate -> intent -> execution chain intact.
"""

from __future__ import annotations

from typing import Optional

from ShadBotTrader.domain.strategy.ports import Strategy
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import SignalStrength, SignalType, StrategyState


class BracketExitStrategy(Strategy):
    """Emit EXIT whenever the application says a bracket was touched."""

    def __init__(self, version: int = 1, state: StrategyState = StrategyState.READY) -> None:
        self._strategy_id = StrategyId("bracket_exit")
        self._version = StrategyVersion(version)
        self._state = state

    @property
    def strategy_id(self) -> StrategyId:
        return self._strategy_id

    @property
    def version(self) -> StrategyVersion:
        return self._version

    @property
    def state(self) -> StrategyState:
        return self._state

    def evaluate(self, context: StrategyContext) -> Optional[TradingSignal]:
        if self._state in (StrategyState.DISABLED, StrategyState.PAUSED):
            return None
        if context.portfolio is None or context.portfolio.is_flat:
            return self._hold(context, "bracket exit while already flat")

        reason = str(context.metadata.get("bracket_exit_reason", "bracket level touched"))
        return TradingSignal(
            signal_id=f"bracket:{context.symbol}:{context.timestamp}:{reason}",
            strategy_id=self._strategy_id,
            strategy_version=self._version,
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            signal_type=SignalType.EXIT,
            strength=SignalStrength.VERY_STRONG,
            confidence=1.0,
            reason=reason,
            context={
                "bracket_exit": True,
                "bracket_exit_reason": reason,
                **context.metadata,
            },
        )

    def _hold(self, context: StrategyContext, reason: str) -> TradingSignal:
        return TradingSignal(
            signal_id=f"bracket:{context.symbol}:{context.timestamp}:hold",
            strategy_id=self._strategy_id,
            strategy_version=self._version,
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=0.0,
            reason=reason,
        )
