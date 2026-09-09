"""Phase 116 hybrid-head strategy with 1D/4H range-aware TP/SL."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

from ShadBotTrader.domain.ai.prediction_target import HybridHeadForecast, RangeForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.simulation.bracket import TradeBracket
from ShadBotTrader.domain.strategy.ports import Strategy
from ShadBotTrader.domain.strategy.signal import TradingSignal
from ShadBotTrader.domain.strategy.strategy_context import StrategyContext
from ShadBotTrader.domain.strategy.strategy_identity import StrategyId, StrategyVersion
from ShadBotTrader.domain.strategy.strategy_types import (
    SignalStrength,
    SignalType,
    StrategyState,
)
from ShadBotTrader.domain.trading.order import OrderSide

HYBRID_HEAD_FORECAST_KEY = "hybrid_head_forecast"
RANGE_1D_FORECAST_KEY = "range_1d_forecast"
RANGE_4H_FORECAST_KEY = "range_4h_forecast"
RAW_ENTRY_PRICE_KEY = "raw_entry_price"
ROOM_REFERENCE_PRICE_KEY = "range_room_reference_price"


@dataclass(frozen=True)
class HybridRangeAwareConfig:
    """Runtime gates selected by Phase 125 and validated by Phase 113."""

    buy_threshold: float = 0.80
    sell_threshold: float = 0.65
    min_margin: float = 0.05
    min_4h_room: float = 2.0
    min_1d_room: float = 5.0
    min_tp_distance: float = 2.0
    min_sl_distance: float = 2.0
    spread_mode: str = "pct"
    spread_value: float = 0.06
    slippage: float = 0.0

    def __post_init__(self) -> None:
        for name, value in (
            ("buy_threshold", self.buy_threshold),
            ("sell_threshold", self.sell_threshold),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"{name} must be in [0, 1]")
        for name, value in (
            ("min_margin", self.min_margin),
            ("min_4h_room", self.min_4h_room),
            ("min_1d_room", self.min_1d_room),
            ("min_tp_distance", self.min_tp_distance),
            ("min_sl_distance", self.min_sl_distance),
            ("spread_value", self.spread_value),
            ("slippage", self.slippage),
        ):
            if value < 0:
                raise ValidationError(f"{name} must not be negative")
        if self.spread_mode not in ("pct", "fixed"):
            raise ValidationError("spread_mode must be 'pct' or 'fixed'")

    def to_dict(self) -> Dict[str, float | str]:
        return {
            "buy_threshold": self.buy_threshold,
            "sell_threshold": self.sell_threshold,
            "min_margin": self.min_margin,
            "min_4h_room": self.min_4h_room,
            "min_1d_room": self.min_1d_room,
            "min_tp_distance": self.min_tp_distance,
            "min_sl_distance": self.min_sl_distance,
            "spread_mode": self.spread_mode,
            "spread_value": self.spread_value,
            "slippage": self.slippage,
        }


class HybridRangeAwareStrategy(Strategy):
    """Turns the hybrid head plus 1D/4H range forecasts into BUY/SELL/HOLD.

    The strategy is the Phase 116 integration layer. It consumes forecasts
    already prepared by an application service or audit script and emits a
    normal :class:`TradingSignal`, so the existing decision engine, risk gate,
    intent factory and journals remain unchanged.
    """

    def __init__(
        self,
        config: HybridRangeAwareConfig | None = None,
        version: int = 1,
        state: StrategyState = StrategyState.READY,
    ) -> None:
        self._config = config or HybridRangeAwareConfig()
        self._strategy_id = StrategyId("hybrid_range_aware")
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

    @property
    def config(self) -> HybridRangeAwareConfig:
        return self._config

    def evaluate(self, context: StrategyContext) -> Optional[TradingSignal]:
        if self._state in (StrategyState.DISABLED, StrategyState.PAUSED):
            return None

        forecast = _forecast(context, HYBRID_HEAD_FORECAST_KEY)
        if not isinstance(forecast, HybridHeadForecast):
            return self._hold(context, "no hybrid head forecast available")

        range_1d = _forecast(context, RANGE_1D_FORECAST_KEY)
        range_4h = _forecast(context, RANGE_4H_FORECAST_KEY)
        if not isinstance(range_1d, RangeForecast):
            return self._hold(context, "no 1D range forecast available", forecast.confidence)
        if not isinstance(range_4h, RangeForecast):
            return self._hold(context, "no 4H range forecast available", forecast.confidence)
        if not range_1d.is_coherent:
            return self._hold(context, "1D range forecast is incoherent", forecast.confidence)
        if not range_4h.is_coherent:
            return self._hold(context, "4H range forecast is incoherent", forecast.confidence)

        side = self._select_side(forecast)
        if side is None:
            return self._hold(context, self._threshold_reason(forecast), forecast.confidence)

        raw_entry = _positive_float(context.metadata.get(RAW_ENTRY_PRICE_KEY))
        if raw_entry is None:
            latest = context.latest_candle
            raw_entry = None if latest is None else float(latest.close.amount)
        if raw_entry is None or raw_entry <= 0:
            return self._hold(context, "no positive entry reference price", forecast.confidence)

        entry = self._entry_price(raw_entry, side)
        room_reference = (
            _positive_float(context.metadata.get(ROOM_REFERENCE_PRICE_KEY)) or raw_entry
        )
        room = self._room(range_1d, range_4h, room_reference, side)
        if side is OrderSide.BUY:
            if room["range_4h_room"] < self._config.min_4h_room:
                return self._hold(
                    context,
                    f"4H BUY room {room['range_4h_room']:.2f} < {self._config.min_4h_room:.2f}",
                    forecast.confidence,
                )
            if room["range_1d_room"] < self._config.min_1d_room:
                return self._hold(
                    context,
                    f"1D BUY room {room['range_1d_room']:.2f} < {self._config.min_1d_room:.2f}",
                    forecast.confidence,
                )
            take_profit = min(range_4h.predicted_high, range_1d.predicted_high)
            stop_loss = range_4h.predicted_low
            if take_profit <= entry or stop_loss >= entry or stop_loss <= 0:
                return self._hold(context, "invalid BUY TP/SL bracket", forecast.confidence)
        else:
            if room["range_4h_room"] < self._config.min_4h_room:
                return self._hold(
                    context,
                    f"4H SELL room {room['range_4h_room']:.2f} < {self._config.min_4h_room:.2f}",
                    forecast.confidence,
                )
            if room["range_1d_room"] < self._config.min_1d_room:
                return self._hold(
                    context,
                    f"1D SELL room {room['range_1d_room']:.2f} < {self._config.min_1d_room:.2f}",
                    forecast.confidence,
                )
            take_profit = max(range_4h.predicted_low, range_1d.predicted_low)
            stop_loss = range_4h.predicted_high
            if take_profit >= entry or stop_loss <= entry or stop_loss <= 0:
                return self._hold(context, "invalid SELL TP/SL bracket", forecast.confidence)

        tp_distance = abs(take_profit - entry)
        sl_distance = abs(entry - stop_loss)
        if tp_distance < self._config.min_tp_distance:
            return self._hold(
                context,
                f"TP distance {tp_distance:.2f} < {self._config.min_tp_distance:.2f}",
                forecast.confidence,
            )
        if sl_distance < self._config.min_sl_distance:
            return self._hold(
                context,
                f"SL distance {sl_distance:.2f} < {self._config.min_sl_distance:.2f}",
                forecast.confidence,
            )

        bracket = self._bracket(side, entry, take_profit, stop_loss, context)
        details: Dict[str, Any] = {
            "hybrid_head": forecast.to_dict(),
            "thresholds": self._config.to_dict(),
            "signal_type": SignalType.BUY.value if side is OrderSide.BUY else SignalType.SELL.value,
            "entry_price": entry,
            "raw_entry_price": raw_entry,
            "room_reference_price": room_reference,
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "tp_distance": tp_distance,
            "sl_distance": sl_distance,
            "range_1d": range_1d.to_dict(),
            "range_4h": range_4h.to_dict(),
            "range_room": room,
            "trade_bracket": bracket.to_dict(),
            **context.metadata,
        }
        signal_type = SignalType.BUY if side is OrderSide.BUY else SignalType.SELL
        return TradingSignal(
            signal_id=self._signal_id(context),
            strategy_id=self._strategy_id,
            strategy_version=self._version,
            symbol=context.symbol,
            timeframe=context.timeframe,
            timestamp=context.timestamp,
            signal_type=signal_type,
            strength=self._strength(forecast, side),
            confidence=self._side_probability(forecast, side),
            reason=self._accepted_reason(forecast, side, take_profit, stop_loss),
            context=details,
        )

    def _select_side(self, forecast: HybridHeadForecast) -> OrderSide | None:
        buy_ok = (
            forecast.buy_probability >= self._config.buy_threshold
            and forecast.buy_probability - forecast.sell_probability >= self._config.min_margin
            and forecast.buy_probability - forecast.hold_probability >= self._config.min_margin
        )
        sell_ok = (
            forecast.sell_probability >= self._config.sell_threshold
            and forecast.sell_probability - forecast.buy_probability >= self._config.min_margin
            and forecast.sell_probability - forecast.hold_probability >= self._config.min_margin
        )
        if buy_ok and not sell_ok:
            return OrderSide.BUY
        if sell_ok and not buy_ok:
            return OrderSide.SELL
        return None

    def _threshold_reason(self, forecast: HybridHeadForecast) -> str:
        return (
            "hybrid probabilities below gate: "
            f"sell={forecast.sell_probability:.3f}, hold={forecast.hold_probability:.3f}, "
            f"buy={forecast.buy_probability:.3f}, "
            f"thresholds={self._config.sell_threshold:.2f}/{self._config.buy_threshold:.2f}, "
            f"margin={self._config.min_margin:.2f}"
        )

    def _entry_price(self, raw_entry: float, side: OrderSide) -> float:
        half_spread = (
            _spread_abs(raw_entry, self._config.spread_mode, self._config.spread_value) / 2.0
        )
        if side is OrderSide.BUY:
            return raw_entry + half_spread + self._config.slippage
        return raw_entry - half_spread - self._config.slippage

    @staticmethod
    def _room(
        range_1d: RangeForecast,
        range_4h: RangeForecast,
        reference: float,
        side: OrderSide,
    ) -> Dict[str, float]:
        if side is OrderSide.BUY:
            return {
                "range_4h_room": range_4h.predicted_high - reference,
                "range_1d_room": range_1d.predicted_high - reference,
            }
        return {
            "range_4h_room": reference - range_4h.predicted_low,
            "range_1d_room": reference - range_1d.predicted_low,
        }

    @staticmethod
    def _bracket(
        side: OrderSide,
        entry: float,
        take_profit: float,
        stop_loss: float,
        context: StrategyContext,
    ) -> TradeBracket:
        model_high = take_profit if side is OrderSide.BUY else stop_loss
        model_low = stop_loss if side is OrderSide.BUY else take_profit
        return TradeBracket(
            side=side,
            entry_reference=Price(Decimal(str(entry))),
            take_profit=Price(Decimal(str(take_profit))),
            stop_loss=Price(Decimal(str(stop_loss))),
            created_at=context.timestamp,
            model_high=Price(Decimal(str(model_high))),
            model_low=Price(Decimal(str(model_low))),
            model_reference=Price(Decimal(str(entry))),
        )

    @staticmethod
    def _side_probability(forecast: HybridHeadForecast, side: OrderSide) -> float:
        if side is OrderSide.BUY:
            return forecast.buy_probability
        return forecast.sell_probability

    def _accepted_reason(
        self,
        forecast: HybridHeadForecast,
        side: OrderSide,
        take_profit: float,
        stop_loss: float,
    ) -> str:
        probability = self._side_probability(forecast, side)
        return (
            f"hybrid {side.value} {probability:.1%}; " f"TP {take_profit:.2f}, SL {stop_loss:.2f}"
        )

    def _strength(self, forecast: HybridHeadForecast, side: OrderSide) -> SignalStrength:
        threshold = (
            self._config.buy_threshold if side is OrderSide.BUY else self._config.sell_threshold
        )
        probability = self._side_probability(forecast, side)
        headroom = 1.0 - threshold
        if headroom <= 0:
            return SignalStrength.VERY_STRONG
        ratio = (probability - threshold) / headroom
        if ratio >= 0.75:
            return SignalStrength.VERY_STRONG
        if ratio >= 0.5:
            return SignalStrength.STRONG
        if ratio >= 0.25:
            return SignalStrength.NORMAL
        return SignalStrength.WEAK

    def _signal_id(self, context: StrategyContext) -> str:
        return f"hybrid-range:{context.symbol}:{context.timestamp}"

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
            context={"rejected": True, "reason": reason, **context.metadata},
        )


def _forecast(context: StrategyContext, key: str) -> Any:
    for prediction in context.predictions:
        value = prediction.metadata.get(key)
        if value is not None:
            return value
    return None


def _positive_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None


def _spread_abs(price: float, mode: str, value: float) -> float:
    if mode == "fixed":
        return max(0.0, value)
    return max(0.0, price * value / 100.0)
