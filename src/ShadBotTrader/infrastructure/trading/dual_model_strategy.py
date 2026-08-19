"""Strategy driven by both Phase 29 models (Phase 31).

``AiDirectionalStrategy`` reads one number. This strategy reads both
models and only trades when they agree:

    signal model  ->  buy / sell, with probabilities
    range  model  ->  the high and low expected over the horizon

The signal model proposes a direction; the range model decides whether
that direction is worth taking. A 90%-confident buy with 2 dollars of
predicted upside and 20 of predicted downside is a bad trade, and only
the second model can say so.

Every rejection carries its reason, so a quiet day is explainable rather
than mysterious.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
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

#: Metadata keys the live service uses to attach the two forecasts.
SIGNAL_FORECAST_KEY = "signal_forecast"
RANGE_FORECAST_KEY = "range_forecast"


class DualModelStrategy(Strategy):
    """Combines the signal and range models into one trading opinion.

        Gates applied in order, each one auditable:

        1. both forecasts must be present
        2. the binary BUY/SELL confidence must clear ``min_confidence``
        3. the range model must be internally coherent (high above low)
        4. reward/risk in the signal's direction must clear ``min_reward_risk``
        5. the predicted move must be big enough to survive costs

    A HOLD returned by this strategy means "do not trade because a gate
    rejected the setup"; it is not a third class emitted by the signal model.
    """

    def __init__(
        self,
        min_confidence: float = 0.60,
        min_reward_risk: Optional[float] = 1.2,
        min_move_fraction: float = 0.0008,
        require_range_model: bool = True,
        version: int = 1,
        state: StrategyState = StrategyState.READY,
    ) -> None:
        if not 0.0 <= min_confidence <= 1.0:
            raise ValidationError("min_confidence must be in [0, 1]")
        if min_reward_risk is not None and min_reward_risk <= 0:
            raise ValidationError("min_reward_risk must be positive when enabled")
        if min_move_fraction < 0:
            raise ValidationError("min_move_fraction must not be negative")

        self._strategy_id = StrategyId("dual_model")
        self._version = StrategyVersion(version)
        self._min_confidence = float(min_confidence)
        self._min_reward_risk = None if min_reward_risk is None else float(min_reward_risk)
        self._min_move = float(min_move_fraction)
        self._require_range = require_range_model
        self._state = state

    # -- identity ----------------------------------------------------------
    @property
    def strategy_id(self) -> StrategyId:
        return self._strategy_id

    @property
    def version(self) -> StrategyVersion:
        return self._version

    @property
    def state(self) -> StrategyState:
        return self._state

    # -- evaluation --------------------------------------------------------
    def evaluate(self, context: StrategyContext) -> Optional[TradingSignal]:
        if self._state in (StrategyState.DISABLED, StrategyState.PAUSED):
            return None

        signal = _forecast(context, SIGNAL_FORECAST_KEY)
        if not isinstance(signal, SignalForecast):
            return self._hold(context, "no signal forecast available")

        range_forecast = _forecast(context, RANGE_FORECAST_KEY)
        if self._require_range and not isinstance(range_forecast, RangeForecast):
            return self._hold(
                context,
                "no range forecast available",
                confidence=signal.confidence,
            )

        # --- gate 2: not confident enough ---------------------------------
        predicted = signal.predicted_class.label
        if signal.confidence < self._min_confidence:
            return self._hold(
                context,
                f"confidence {signal.confidence:.1%} < {self._min_confidence:.1%}",
                confidence=signal.confidence,
            )

        wants_buy = predicted == "buy"
        details: Dict[str, Any] = {
            "signal_class": predicted,
            "confidence": signal.confidence,
            "sell_probability": signal.sell_probability,
            "buy_probability": signal.buy_probability,
            "directional_confidence": signal.directional_confidence,
        }

        if isinstance(range_forecast, RangeForecast):
            # --- gate 4: a broken range forecast is not usable ------------
            if not range_forecast.is_coherent:
                return self._hold(
                    context,
                    "range model predicted a high below its own low",
                    confidence=signal.confidence,
                )

            upside = range_forecast.upside
            downside = range_forecast.downside
            # Reward and risk swap meaning for a short.
            reward = upside if wants_buy else downside
            risk = downside if wants_buy else upside

            details.update(
                {
                    "predicted_high": range_forecast.predicted_high,
                    "predicted_low": range_forecast.predicted_low,
                    "reward": reward,
                    "risk": risk,
                }
            )

            # --- gate 5: the move must pay for the risk -------------------
            if risk > 0:
                ratio = reward / risk
                details["reward_risk"] = ratio
                if self._min_reward_risk is not None and ratio < self._min_reward_risk:
                    return self._hold(
                        context,
                        f"reward/risk {ratio:.2f} < {self._min_reward_risk:.2f}",
                        confidence=signal.confidence,
                    )
            elif reward <= 0:
                # No predicted movement in either direction.
                return self._hold(
                    context,
                    "range model predicts no move worth trading",
                    confidence=signal.confidence,
                )

            # --- gate 6: the move must survive costs ----------------------
            reference = range_forecast.reference_close
            if reference > 0:
                move_fraction = reward / reference
                details["move_fraction"] = move_fraction
                if move_fraction < self._min_move:
                    return self._hold(
                        context,
                        f"predicted move {move_fraction:.4%} below the "
                        f"{self._min_move:.4%} cost floor",
                        confidence=signal.confidence,
                    )

        return TradingSignal(
            signal_id=self._signal_id(context),
            strategy_id=self._strategy_id,
            strategy_version=self._version,
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            signal_type=SignalType.BUY if wants_buy else SignalType.SELL,
            strength=self._strength(signal.confidence),
            confidence=signal.confidence,
            reason=self._describe(signal, range_forecast, wants_buy, details),
            context=details,
        )

    # -- helpers -----------------------------------------------------------
    def _describe(
        self,
        signal: SignalForecast,
        range_forecast: Any,
        wants_buy: bool,
        details: Dict[str, Any],
    ) -> str:
        text = f"signal {signal.describe()}"
        if isinstance(range_forecast, RangeForecast):
            target = range_forecast.predicted_high if wants_buy else range_forecast.predicted_low
            text += f", target {target:.2f}"
            # Report the ratio the gate actually used. ``RangeForecast``
            # exposes upside/downside, which is the long-oriented view; for
            # a short those two swap, and printing the raw property would
            # contradict the gate that just passed the trade.
            ratio = details.get("reward_risk")
            if isinstance(ratio, float):
                text += f", r/r {ratio:.2f}"
        return text

    def _strength(self, confidence: float) -> SignalStrength:
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

    def _signal_id(self, context: StrategyContext) -> str:
        return f"dual:{context.symbol}:{context.timestamp}"

    def _hold(
        self,
        context: StrategyContext,
        reason: str,
        confidence: float = 0.0,
    ) -> TradingSignal:
        """A HOLD carrying why — a quiet day must be explainable."""
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
            context={"rejected": True},
        )


def _forecast(context: StrategyContext, key: str) -> Any:
    """Pull a forecast off whichever prediction carries it."""
    for prediction in context.predictions:
        value = prediction.metadata.get(key)
        if value is not None:
            return value
    return None
