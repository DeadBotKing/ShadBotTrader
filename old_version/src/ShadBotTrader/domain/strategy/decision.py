"""Trading decision (Phase 14, sections 17-18).

INVARIANT: a ``TradingDecision`` is NOT an ``Order``. A decision says
"enter long XAUUSD"; turning that into a broker order is the Execution
Platform's job, and it may only do so via a ``TradingIntent`` that has
passed the risk gate.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import DecisionType, RejectionReason


class TradingDecision(ValueObject):
    """The outcome of evaluating a validated signal against policy."""

    def __init__(
        self,
        decision_id: str,
        strategy_id: StrategyId,
        strategy_version: StrategyVersion,
        symbol: Symbol,
        timestamp: Timestamp,
        decision_type: DecisionType,
        confidence: float = 0.0,
        reason: str = "",
        rejection_reason: Optional[RejectionReason] = None,
        source_signal_id: str = "",
        context: Mapping[str, Any] | None = None,
    ) -> None:
        if not decision_id.strip():
            raise ValidationError("decision_id must not be empty")
        if not 0.0 <= confidence <= 1.0:
            raise ValidationError("Decision confidence must be in [0, 1]")

        self._decision_id = decision_id.strip()
        self._strategy_id = strategy_id
        self._strategy_version = strategy_version
        self._symbol = symbol
        self._timestamp = timestamp
        self._decision_type = decision_type
        self._confidence = float(confidence)
        self._reason = reason
        self._rejection_reason = rejection_reason
        self._source_signal_id = source_signal_id
        self._context: Dict[str, Any] = dict(context or {})

    @classmethod
    def hold(
        cls,
        decision_id: str,
        signal: TradingSignal,
        reason: str,
        rejection_reason: Optional[RejectionReason] = None,
    ) -> "TradingDecision":
        """Build a HOLD decision carrying an explicit reason."""
        return cls(
            decision_id=decision_id,
            strategy_id=signal.strategy_id,
            strategy_version=signal.strategy_version,
            symbol=signal.symbol,
            timestamp=signal.timestamp,
            decision_type=DecisionType.HOLD,
            confidence=signal.confidence,
            reason=reason,
            rejection_reason=rejection_reason,
            source_signal_id=signal.signal_id,
        )

    @property
    def decision_id(self) -> str:
        return self._decision_id

    @property
    def strategy_id(self) -> StrategyId:
        return self._strategy_id

    @property
    def strategy_version(self) -> StrategyVersion:
        return self._strategy_version

    @property
    def symbol(self) -> Symbol:
        return self._symbol

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def decision_type(self) -> DecisionType:
        return self._decision_type

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def rejection_reason(self) -> Optional[RejectionReason]:
        return self._rejection_reason

    @property
    def source_signal_id(self) -> str:
        return self._source_signal_id

    @property
    def context(self) -> Dict[str, Any]:
        return dict(self._context)

    @property
    def is_actionable(self) -> bool:
        """True when the decision requires an intent (not HOLD)."""
        return self._decision_type is not DecisionType.HOLD

    def _value(self) -> tuple[Any, ...]:
        return (
            self._decision_id,
            self._strategy_id,
            self._strategy_version,
            self._symbol,
            self._timestamp,
            self._decision_type,
            self._confidence,
            self._rejection_reason,
        )
