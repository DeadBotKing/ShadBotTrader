"""Causal two-timeframe prediction source for model-driven backtests.

The signal model is evaluated on the latest closed 5M candle window first.
Only when BUY or SELL wins with the configured confidence does this source
prepare the 1H window and ask the range model for its high/low forecast.

The source is intentionally stateful because the simulation engine delivers
one market event at a time.  At decision time it can see only:

* signal candles already delivered by the engine; and
* 1H candles whose close time is no later than that decision time.

No future range candle is read merely because it exists in the historical
input sequence.
"""

from __future__ import annotations

from bisect import bisect_right
from collections import deque
from datetime import timedelta
from decimal import Decimal
from typing import Any, Deque, Dict, List, Optional, Sequence

from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.price import Price
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.domain.simulation.bracket import TradeBracket
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.domain.simulation.ports import PredictionSource
from ShadBotTrader.domain.trading.order import OrderSide


class DualModelPredictionSource(PredictionSource):
    """Run signal-first inference over 5M data with a 1H range model."""

    def __init__(
        self,
        signal_artifact: Any,
        signal_predictor: Any,
        range_artifact: Any,
        range_predictor: Any,
        symbol: Symbol,
        signal_timeframe: Timeframe = Timeframe("5M"),
        range_timeframe: Timeframe = Timeframe("1H"),
        range_candles: Sequence[Candle] = (),
        signal_window_size: int = 100,
        range_window_size: int = 500,
        min_signal_confidence: float = 0.60,
        feature_set: Any = None,
        resolver: Any = None,
        signal_feature_source: Any = None,
        range_feature_source: Any = None,
        hold_confidence_penalty: float = 0.5,
        signal_matrix: Any = None,
        range_matrix: Any = None,
        signal_candles: Sequence[Candle] = (),
        reward_risk_multiplier: Optional[float] = None,
        spread: Optional[Decimal] = None,
        spread_pct: Optional[Decimal] = None,
    ) -> None:
        if signal_window_size < 2 or range_window_size < 2:
            raise ValidationError("Both model windows must be >= 2")
        if not 0.0 <= min_signal_confidence <= 1.0:
            raise ValidationError("min_signal_confidence must be in [0, 1]")
        if not 0.0 <= hold_confidence_penalty <= 1.0:
            raise ValidationError("hold_confidence_penalty must be in [0, 1]")
        if reward_risk_multiplier is not None and reward_risk_multiplier <= 0:
            raise ValidationError("reward_risk_multiplier must be positive")

        self._signal_artifact = signal_artifact
        self._signal_predictor = signal_predictor
        self._range_artifact = range_artifact
        self._range_predictor = range_predictor
        self._symbol = symbol
        self._signal_timeframe = signal_timeframe
        self._range_timeframe = range_timeframe
        self._signal_window_size = signal_window_size
        self._range_window_size = range_window_size
        self._min_signal_confidence = float(min_signal_confidence)
        self._feature_set = feature_set
        self._resolver = resolver
        self._signal_feature_source = signal_feature_source
        self._range_feature_source = range_feature_source
        self._signal_matrix = signal_matrix
        self._range_matrix = range_matrix
        self._reward_risk_multiplier = reward_risk_multiplier
        self._spread_fixed = spread
        self._spread_pct_val = spread_pct
        self._signal_candle_index = {
            candle.open_time.value: index for index, candle in enumerate(signal_candles)
        }
        self._hold_penalty = float(hold_confidence_penalty)

        self._signal_candles: Deque[Candle] = deque(
            maxlen=max(signal_window_size * 2, signal_window_size + 100)
        )
        self._range_candles: Deque[Candle] = deque(
            maxlen=max(range_window_size * 2, range_window_size + 100)
        )
        self._all_range_candles = sorted(range_candles, key=lambda candle: candle.open_time.value)
        self._range_candle_index = {
            candle.open_time.value: index for index, candle in enumerate(self._all_range_candles)
        }
        self._range_cursor = 0
        self._bars_seen = 0
        self._signal_predictions = 0
        self._range_predictions = 0
        self._abstentions = 0
        self._last_signal: Optional[SignalForecast] = None
        self._last_range: Optional[RangeForecast] = None
        self._last_value: Optional[float] = None
        self._last_error: str = ""
        self._error_counts: Dict[str, int] = {}

        self._signal_delta = _timeframe_delta(str(signal_timeframe))
        self._range_delta = _timeframe_delta(str(range_timeframe))
        # باگ ۵۰ (فاز ۶۷): کندل‌های 1Dِ «بسته‌شدهٔ قبل از شروع replay» باید
        # از اول در بافر باشند — وگرنه اولین سیگنال‌های actionable تا
        # نزدیک window×1D از شروع replay بدون رنج می‌مانند (اجرای کاربر:
        # ۹٬۰۰۰×5M=۳۱ روز → فقط ۳۱ کندل 1D → مدل ۱۵۰تایی هیچ‌وقت رنج
        # نمی‌داد). cursor را جلو می‌بریم تا observe دوباره اضافه نکند.
        if self._all_range_candles and signal_candles:
            first_signal_time = min(c.open_time.value for c in signal_candles)
            while self._range_cursor < len(self._all_range_candles):
                candidate = self._all_range_candles[self._range_cursor]
                if candidate.open_time.value + self._range_delta > first_signal_time:
                    break
                self._range_candles.append(candidate)
                self._range_cursor += 1

    # ------------------------------------------------------------ state --
    @property
    def last_forecast(self) -> Optional[SignalForecast]:
        """The latest signal forecast, kept for the existing source API."""
        return self._last_signal

    @property
    def last_signal_forecast(self) -> Optional[SignalForecast]:
        return self._last_signal

    @property
    def last_range_forecast(self) -> Optional[RangeForecast]:
        return self._last_range

    @property
    def predictions_made(self) -> int:
        return self._signal_predictions

    @property
    def range_predictions_made(self) -> int:
        return self._range_predictions

    @property
    def abstentions(self) -> int:
        return self._abstentions

    @property
    def min_signal_confidence(self) -> float:
        """The confidence gate this source applies to signal forecasts."""
        return self._min_signal_confidence

    @property
    def last_error(self) -> str:
        return self._last_error

    def stats(self) -> Dict[str, Any]:
        return {
            "bars_seen": self._bars_seen,
            "errors": dict(self._error_counts),
            "signal_predictions": self._signal_predictions,
            "range_predictions": self._range_predictions,
            "abstentions": self._abstentions,
            "signal_window_size": self._signal_window_size,
            "range_window_size": self._range_window_size,
            "min_signal_confidence": self._min_signal_confidence,
        }

    # ------------------------------------------------------------- port --
    def observe(self, event: MarketEvent) -> None:
        """Accept only the bar the engine just delivered."""
        candle = event.candle
        if candle is None:
            return
        self._signal_candles.append(candle)
        self._bars_seen += 1

        # An event at the open of a 5M candle represents its completed
        # information for this historical replay.  The decision can be
        # made at that candle's close, hence +5M here.  A 1H bar is usable
        # only after its own close, never while it is still forming.
        decision_time = event.event_time.value + self._signal_delta
        while self._range_cursor < len(self._all_range_candles):
            candidate = self._all_range_candles[self._range_cursor]
            close_time = candidate.open_time.value + self._range_delta
            if close_time > decision_time:
                break
            self._range_candles.append(candidate)
            self._range_cursor += 1

    def predict(self, event: MarketEvent) -> Optional[float]:
        """Predict signal first; call the range model only when actionable."""
        self._last_error = ""
        self._last_range = None
        if len(self._signal_candles) < self._signal_window_size:
            self._abstentions += 1
            return None

        signal_window = self._build_window(
            self._signal_candles,
            self._signal_timeframe,
            self._signal_feature_source,
            self._signal_window_size,
            matrix=self._signal_matrix,
            original_index=self._signal_candle_index.get(event.event_time.value),
            model_role="signal",
        )
        if signal_window is None:
            self._abstentions += 1
            return None

        try:
            signal = self._signal_predictor.forecast(
                self._signal_artifact,
                signal_window,
                generated_at=str(event.event_time),
            )
        except Exception as error:
            self._last_error = f"signal inference failed: {type(error).__name__}: {error}"
            key = f"signal: {type(error).__name__}: {str(error)[:80]}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
            self._abstentions += 1
            return None

        self._last_signal = signal
        self._signal_predictions += 1
        # Binary signal: buy probability is the directional value.  There
        # is no HOLD output to pull toward neutral; a low winning
        # probability is handled by the confidence gate below.
        value = signal.directional_confidence
        self._last_value = float(value)

        # This is the explicit BUY/SELL probability gate requested by the
        # user. Only a winning binary direction above the threshold reaches
        # the range model.
        if not signal.is_actionable(self._min_signal_confidence):
            return self._last_value

        if len(self._range_candles) < self._range_window_size:
            self._abstentions += 1
            return self._last_value

        latest_range = self._range_candles[-1]
        range_window = self._build_window(
            self._range_candles,
            self._range_timeframe,
            self._range_feature_source,
            self._range_window_size,
            matrix=self._range_matrix,
            original_index=self._range_candle_index.get(latest_range.open_time.value),
            model_role="range",
        )
        if range_window is None:
            self._abstentions += 1
            return self._last_value

        latest_range = self._range_candles[-1]
        try:
            self._last_range = self._range_predictor.forecast(
                self._range_artifact,
                range_window,
                reference_close=float(latest_range.close.amount),
                generated_at=str(latest_range.open_time),
            )
            self._range_predictions += 1
        except Exception as error:
            self._last_error = f"range inference failed: {type(error).__name__}: {error}"
            key = f"range: {type(error).__name__}: {str(error)[:80]}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
            self._last_range = None
        return self._last_value

    def confidence(self, event: MarketEvent) -> float:
        """Confidence of the latest signal forecast."""
        if self._last_signal is None:
            return 0.0
        return self._last_signal.confidence

    def reset(self) -> None:
        self._signal_candles.clear()
        self._range_candles.clear()
        self._range_cursor = 0
        self._bars_seen = 0
        self._signal_predictions = 0
        self._range_predictions = 0
        self._abstentions = 0
        self._last_signal = None
        self._last_range = None
        self._last_value = None
        self._last_error = ""
        self._error_counts = {}

    # -------------------------------------------------------- brackets --
    def bracket_for(
        self,
        event: MarketEvent,
        side: OrderSide,
        entry_reference: Price,
    ) -> Optional[TradeBracket]:
        """Turn the latest range forecast into fixed TP/SL levels.

        فاز ۵۷: spread به from_model_levels پاس میشه
        تا SL به اندازه spread گسترش پیدا کنه.
        """
        forecast = self._last_range
        if forecast is None or not forecast.is_coherent:
            return None

        # spread دلاری محاسبه کن
        spread_amount: Optional[Decimal] = None
        try:
            from decimal import Decimal as _D

            if self._spread_pct_val is not None:
                # درصدی: spread = قیمت × pct
                spread_amount = _D(str(float(entry_reference.amount) * float(self._spread_pct_val)))
            elif self._spread_fixed is not None:
                spread_amount = self._spread_fixed
        except Exception:
            pass

        try:
            return TradeBracket.from_model_levels(
                side=side,
                entry_reference=entry_reference,
                predicted_high=forecast.predicted_high,
                predicted_low=forecast.predicted_low,
                created_at=event.event_time,
                model_reference=forecast.reference_close,
                reward_risk_multiplier=self._reward_risk_multiplier,
                spread=spread_amount,
            )
        except ValidationError:
            return None

    # -------------------------------------------------------- internals --
    def _build_window(
        self,
        candles: Sequence[Candle],
        timeframe: Timeframe,
        feature_source: Any,
        window_size: int,
        matrix: Any = None,
        original_index: Optional[int] = None,
        model_role: Optional[str] = None,
    ) -> Optional[List[List[float]]]:
        if matrix is not None and original_index is not None:
            # The full-series matrix is computed once by the application
            # service.  Slicing it here keeps a long backtest from
            # recomputing hundreds of indicators for every 5M bar.
            positions = bisect_right(matrix.source_index, original_index)
            if positions < window_size:
                return None
            return [list(row) for row in matrix.rows[positions - window_size : positions]]

        from ShadBotTrader.infrastructure.ai.feature_matrix import build_feature_matrix

        try:
            matrix = build_feature_matrix(
                candles=list(candles),
                symbol=self._symbol,
                timeframe=timeframe,
                feature_set=self._feature_set,
                resolver=self._resolver,
                include_features=self._feature_set is not None and self._resolver is not None,
                source=feature_source,
                causal_only=True,
                model_role=model_role,
            )
        except Exception as error:
            self._last_error = f"feature window failed: {type(error).__name__}: {error}"
            key = f"features: {type(error).__name__}: {str(error)[:80]}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
            return None

        if len(matrix) < window_size:
            return None
        # Predictors apply the model's one per-window scaling. Returning raw
        # rows here also keeps this source consistent with LiveMatrixBuilder.
        return [list(row) for row in matrix.rows[-window_size:]]


def _timeframe_delta(label: str) -> timedelta:
    text = str(label).strip().upper()
    digits = "".join(character for character in text if character.isdigit())
    amount = int(digits) if digits else 1
    if text.endswith("M"):
        return timedelta(minutes=amount)
    if text.endswith("H"):
        return timedelta(hours=amount)
    if text.endswith("D"):
        return timedelta(days=amount)
    raise ValidationError(f"Unsupported timeframe for dual-model backtest: {label}")
