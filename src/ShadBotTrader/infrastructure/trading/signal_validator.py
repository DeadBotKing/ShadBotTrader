"""Default signal validation (Phase 14, section 16).

Checks the structural and temporal validity of a signal before it is
allowed to influence a decision: matching symbol/timeframe, a non-future
timestamp, an enabled strategy and a minimum confidence.
"""

from __future__ import annotations

from ShadBotTrader.domain.strategy.ports import SignalValidator
from ShadBotTrader.domain.strategy.risk_policy import RiskVerdict
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_types import RejectionReason, SignalType


class DefaultSignalValidator(SignalValidator):
    """Structural + freshness validation of a trading signal."""

    def __init__(
        self,
        min_confidence: float = 0.0,
        max_signal_age_seconds: float = 300.0,
        reject_hold: bool = False,
    ) -> None:
        self._min_confidence = float(min_confidence)
        self._max_age = float(max_signal_age_seconds)
        self._reject_hold = reject_hold

    def validate(self, signal: TradingSignal, context: StrategyContext) -> RiskVerdict:
        if signal.symbol != context.symbol:
            return RiskVerdict.reject(
                RejectionReason.SYMBOL_MISMATCH,
                f"signal symbol {signal.symbol} != context symbol {context.symbol}",
            )
        if signal.timeframe != context.timeframe:
            return RiskVerdict.reject(
                RejectionReason.TIMEFRAME_MISMATCH,
                f"signal timeframe {signal.timeframe} != context {context.timeframe}",
            )

        age = (context.timestamp.value - signal.timestamp.value).total_seconds()
        if age < 0:
            return RiskVerdict.reject(
                RejectionReason.SCHEMA_MISMATCH,
                "signal timestamp lies in the future relative to the context",
            )
        if age > self._max_age:
            return RiskVerdict.reject(
                RejectionReason.STALE_PREDICTION,
                f"signal is {age:.0f}s old (max {self._max_age:.0f}s)",
            )

        if self._reject_hold and signal.signal_type is SignalType.HOLD:
            return RiskVerdict.reject(RejectionReason.NO_SIGNAL, "signal is HOLD")

        if signal.is_actionable and signal.confidence < self._min_confidence:
            return RiskVerdict.reject(
                RejectionReason.LOW_CONFIDENCE,
                f"confidence {signal.confidence:.3f} < {self._min_confidence:.3f}",
            )

        return RiskVerdict.approve()
