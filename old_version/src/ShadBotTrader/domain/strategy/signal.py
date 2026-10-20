"""Trading signal — the output of a strategy (Phase 14, sections 12-15).

A signal is an opinion, never an order. It carries enough provenance
(strategy identity, version, timestamps) to be validated and audited
downstream.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.common.value_object import ValueObject
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import SignalStrength, SignalType


class TradingSignal(ValueObject):
    """A strategy's opinion about a symbol at a point in time.

    ``confidence`` is the *signal* confidence in ``[0, 1]``. It is not the
    same thing as model confidence (Phase 14, section 15): a strategy may
    derive it from a prediction, temper it, or set it independently.
    """

    def __init__(
        self,
        signal_id: str,
        strategy_id: StrategyId,
        strategy_version: StrategyVersion,
        symbol: Symbol,
        timeframe: Timeframe,
        timestamp: Timestamp,
        signal_type: SignalType,
        strength: SignalStrength = SignalStrength.NORMAL,
        confidence: float = 0.0,
        reason: str = "",
        context: Mapping[str, Any] | None = None,
    ) -> None:
        if not signal_id.strip():
            raise ValidationError("signal_id must not be empty")
        if not 0.0 <= confidence <= 1.0:
            raise ValidationError("Signal confidence must be in [0, 1]")

        self._signal_id = signal_id.strip()
        self._strategy_id = strategy_id
        self._strategy_version = strategy_version
        self._symbol = symbol
        self._timeframe = timeframe
        self._timestamp = timestamp
        self._signal_type = signal_type
        self._strength = strength
        self._confidence = float(confidence)
        self._reason = reason
        self._context: Dict[str, Any] = dict(context or {})

    @property
    def signal_id(self) -> str:
        return self._signal_id

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
    def timeframe(self) -> Timeframe:
        return self._timeframe

    @property
    def timestamp(self) -> Timestamp:
        return self._timestamp

    @property
    def signal_type(self) -> SignalType:
        return self._signal_type

    @property
    def strength(self) -> SignalStrength:
        return self._strength

    @property
    def confidence(self) -> float:
        return self._confidence

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def context(self) -> Dict[str, Any]:
        """A copy of the explainability context."""
        return dict(self._context)

    @property
    def is_actionable(self) -> bool:
        """True when the signal asks for a change (not HOLD)."""
        return self._signal_type is not SignalType.HOLD

    def _value(self) -> tuple[Any, ...]:
        return (
            self._signal_id,
            self._strategy_id,
            self._strategy_version,
            self._symbol,
            self._timeframe,
            self._timestamp,
            self._signal_type,
            self._strength,
            self._confidence,
        )
