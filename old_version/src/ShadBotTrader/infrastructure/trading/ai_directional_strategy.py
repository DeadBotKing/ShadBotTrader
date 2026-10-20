"""AI-directional strategy — turns model predictions into signals.

Phase 14, sections 30-32: a strategy may consume AI predictions, but the
*strategy* defines the semantics. This implementation reads a direction
classifier's output and applies explicit thresholds, plus the mandatory
prediction-validity checks (model identity, age, confidence).

The strategy is pure: same context in, same signal out. It never touches
infrastructure and never produces an order.
"""

from __future__ import annotations

from typing import Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.strategy.ports import Strategy
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import (
    SignalStrength,
    SignalType,
    StrategyState,
)


class AiDirectionalStrategy(Strategy):
    """Maps a direction model's prediction to BUY / SELL / HOLD.

    Decision rules (all explicit, all auditable):

    * no prediction from ``model_id``            -> HOLD
    * prediction older than ``max_prediction_age_seconds`` -> HOLD (stale)
    * confidence below ``min_confidence``        -> HOLD (low confidence)
    * value >= 0.5 -> BUY, otherwise SELL

    Strength is derived from how far confidence sits above the minimum,
    so a barely-passing signal is never reported as VERY_STRONG.
    """

    def __init__(
        self,
        model_id: str = "gold_direction",
        min_confidence: float = 0.55,
        max_prediction_age_seconds: float = 300.0,
        version: int = 1,
        state: StrategyState = StrategyState.READY,
    ) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValidationError("min_confidence must be in [0, 1]")
        if max_prediction_age_seconds <= 0:
            raise ValidationError("max_prediction_age_seconds must be positive")

        self._strategy_id = StrategyId("ai_directional")
        self._version = StrategyVersion(version)
        self._model_id = model_id
        self._min_confidence = float(min_confidence)
        self._max_age = float(max_prediction_age_seconds)
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

    @property
    def model_id(self) -> str:
        return self._model_id

    def evaluate(self, context: StrategyContext) -> Optional[TradingSignal]:
        if self._state in (StrategyState.DISABLED, StrategyState.PAUSED):
            return None

        prediction = context.prediction_for(self._model_id)
        if prediction is None:
            return self._hold(context, f"no prediction from '{self._model_id}'")

        age = prediction.age_seconds(context.timestamp)
        if age > self._max_age:
            return self._hold(
                context,
                f"stale prediction ({age:.0f}s > {self._max_age:.0f}s)",
                confidence=prediction.confidence,
            )
        if age < 0:
            # A prediction generated after the decision time would be
            # lookahead; refuse it rather than silently trusting it.
            return self._hold(
                context,
                "prediction generated after the decision timestamp",
                confidence=prediction.confidence,
            )

        if prediction.confidence < self._min_confidence:
            return self._hold(
                context,
                f"confidence {prediction.confidence:.3f} < {self._min_confidence:.3f}",
                confidence=prediction.confidence,
            )

        is_up = prediction.value >= 0.5
        signal_type = SignalType.BUY if is_up else SignalType.SELL
        return TradingSignal(
            signal_id=self._signal_id(context),
            strategy_id=self._strategy_id,
            strategy_version=self._version,
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            signal_type=signal_type,
            strength=self._strength(prediction.confidence),
            confidence=prediction.confidence,
            reason=(
                f"{self._model_id} predicts {'up' if is_up else 'down'} "
                f"(value={prediction.value:.3f}, confidence={prediction.confidence:.3f})"
            ),
            context={
                "model_id": prediction.model_id,
                "model_version": prediction.model_version,
                "prediction_value": prediction.value,
                "prediction_age_seconds": age,
                "regime": context.regime.value,
            },
        )

    # -- helpers ----------------------------------------------------------
    def _strength(self, confidence: float) -> SignalStrength:
        """Grade confidence relative to the acceptance threshold."""
        headroom = 1.0 - self._min_confidence
        if headroom <= 0:
            return SignalStrength.VERY_STRONG
        ratio = (confidence - self._min_confidence) / headroom
        if ratio >= 0.75:
            return SignalStrength.VERY_STRONG
        if ratio >= 0.5:
            return SignalStrength.STRONG
        if ratio >= 0.25:
            return SignalStrength.NORMAL
        return SignalStrength.WEAK

    def _hold(
        self,
        context: StrategyContext,
        reason: str,
        confidence: float = 0.0,
    ) -> TradingSignal:
        return TradingSignal(
            signal_id=self._signal_id(context),
            strategy_id=self._strategy_id,
            strategy_version=self._version,
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            signal_type=SignalType.HOLD,
            strength=SignalStrength.WEAK,
            confidence=confidence,
            reason=reason,
        )

    def _signal_id(self, context: StrategyContext) -> str:
        return (
            f"{self._strategy_id}:{self._version}:"
            f"{context.symbol}:{context.timeframe}:{context.timestamp}"
        )
