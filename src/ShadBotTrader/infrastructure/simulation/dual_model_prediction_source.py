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
        range_target_units: str = "pct",
        trend_filter: str = "none",
        daily_artifact: Any = None,
        daily_predictor: Any = None,
        daily_timeframe: Timeframe = Timeframe("1D"),
        daily_candles: Sequence[Candle] = (),
        daily_matrix: Any = None,
        daily_window_size: int = 150,
        slope_mode: str = "both",
    ) -> None:
        if signal_window_size < 2 or range_window_size < 2:
            raise ValidationError("Both model windows must be >= 2")
        if range_target_units not in ("pct", "atr"):
            raise ValidationError(
                f"Unknown range target units: {range_target_units!r} (use 'pct' or 'atr')"
            )
        if trend_filter not in ("none", "ema50"):
            raise ValidationError(f"Unknown trend filter: {trend_filter!r} (use 'none' or 'ema50')")
        if slope_mode not in ("both", "either", "high", "low"):
            raise ValidationError(
                f"Unknown slope mode: {slope_mode!r} (use 'both', 'either', 'high' or 'low')"
            )
        if daily_predictor is not None and daily_window_size < 2:
            raise ValidationError("daily_window_size must be >= 2 when a daily model is set")
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
        # فاز ۹۵: واحد تارگت مدل رنج — "atr" نیاز به ATR مرجع داره
        self._range_target_units = range_target_units
        self._atr_cache_key: Any = None
        self._atr_cache_value: float = 0.0
        # فاز ۹۶-ب: فیلتر ترند روزانه — "ema50": SHORT ممنوع وقتی close
        # بالای EMA50(1D) و LONG ممنوع وقتی زیر آن (دو دیتاست پشت‌سرهم
        # نشان دادند ضرر اصلی short-در-روند-صعودی است).
        self._trend_filter = trend_filter
        self._trend_blocks = 0
        self._last_trend_block = ""
        # فاز ۹۷ — استراتژی سه‌تایم‌فریمی: مدل رنج 1D برای ترند روز
        # (مجوز ۲: شیب High/Low پیش‌بینی D1 نسبت به D0) و براکت TP/SL
        # از مدل رنج 4H با fallback های D0 و کندل‌های 5M امروز.
        self._daily_artifact = daily_artifact
        self._daily_predictor = daily_predictor
        self._daily_timeframe = daily_timeframe
        self._daily_matrix = daily_matrix
        self._daily_window_size = daily_window_size
        self._slope_mode = slope_mode
        self._all_daily_candles = sorted(daily_candles, key=lambda c: c.open_time.value)
        self._daily_candle_index = {
            candle.open_time.value: index for index, candle in enumerate(self._all_daily_candles)
        }
        self._daily_cursor = 0
        self._daily_delta = _timeframe_delta(str(daily_timeframe))
        self._last_daily: Optional[RangeForecast] = None
        self._last_d0: Optional[Candle] = None
        self._daily_cache_key: Any = None
        self._daily_cache_value: Optional[RangeForecast] = None
        self._daily_window_cache: Dict[Any, Any] = {}
        self._daily_predictions = 0
        self._daily_blocked = 0
        self._sl_fallback_d0 = 0
        self._sl_fallback_today = 0
        self._license3_refused = 0
        self._rr_refused = 0
        self._no_sl_found = 0
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
        self._daily_feed: Deque[Candle] = deque(
            maxlen=max(daily_window_size * 2, daily_window_size + 100)
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
            "range_target_units": self._range_target_units,
            "trend_filter": self._trend_filter,
            "trend_blocked": self._trend_blocks,
            "slope_mode": self._slope_mode,
            "daily_predictions": self._daily_predictions,
            "daily_blocked": self._daily_blocked,
            "sl_fallback_d0": self._sl_fallback_d0,
            "sl_fallback_today": self._sl_fallback_today,
            "license3_refused": self._license3_refused,
            "rr_refused": self._rr_refused,
            "no_sl_found": self._no_sl_found,
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
        # فاز ۹۷: خوراک کندل‌های 1D — فقط کندل‌های بسته تا زمان تصمیم
        while self._daily_cursor < len(self._all_daily_candles):
            candidate = self._all_daily_candles[self._daily_cursor]
            close_time = candidate.open_time.value + self._daily_delta
            if close_time > decision_time:
                break
            self._daily_feed.append(candidate)
            self._daily_cursor += 1

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

        # فاز ۹۶-ب: فیلتر ترند روزانه — قبل از مصرف مدل رنج.
        # "ema50": SHORT ممنوع وقتی آخرین close رنج بالای EMA50 است
        # (بازار صعودی) و LONG ممنوع وقتی زیر آن (بازار نزولی).
        # EMA کاملاً علوی از کندل‌های تحویل‌شده؛ دادهٔ کمتر از دوره →
        # فیلتر بی‌اثر (اجازه) و شمرده می‌شود.
        if self._trend_filter == "ema50":
            blocked, reason = self._trend_blocks_signal(signal)
            if blocked:
                self._trend_blocks += 1
                self._last_trend_block = reason
                return self._last_value

        # ── فاز ۹۷ — مجوز ۲: ترند روزانه از مدل رنج 1D ──────────────
        # پیش‌بینی High/Low روز D1 از کندل‌های روزانه تا D0؛ شیب نسبت به
        # D0 واقعی. خرید: شیب‌ها >= ۰ (بر اساس slope_mode)؛ فروش برعکس.
        # اگر رد شود مدل 4H اجرا نمی‌شود → براکت None → ترید نه.
        if self._daily_predictor is not None:
            daily_forecast, d0 = self._daily_context()
            if daily_forecast is None or d0 is None:
                self._abstentions += 1
                return self._last_value
            slope_high = daily_forecast.predicted_high - float(d0.high.amount)
            slope_low = daily_forecast.predicted_low - float(d0.low.amount)
            wants_buy = signal.predicted_class.label == "buy"
            if self._slope_mode == "both":
                ok = (
                    (slope_high >= 0 and slope_low >= 0)
                    if wants_buy
                    else (slope_high <= 0 and slope_low <= 0)
                )
            elif self._slope_mode == "either":
                ok = (
                    (slope_high >= 0 or slope_low >= 0)
                    if wants_buy
                    else (slope_high <= 0 or slope_low <= 0)
                )
            elif self._slope_mode == "high":
                ok = slope_high >= 0 if wants_buy else slope_high <= 0
            else:  # low
                ok = slope_low >= 0 if wants_buy else slope_low <= 0
            if not ok:
                self._daily_blocked += 1
                self._last_block_reason = (
                    f"daily slope: {signal.predicted_class.label.upper()} blocked "
                    f"(mode={self._slope_mode}, slope_high={slope_high:+.2f}, "
                    f"slope_low={slope_low:+.2f})"
                )
                return self._last_value
            self._last_daily = daily_forecast
            self._last_d0 = d0
            self._daily_predictions += 1

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
            # فاز ۹۵: فقط مدل‌های ATR-unit کلمهٔ atr_reference را می‌گیرند —
            # پیش‌بینی‌کننده‌های قدیمی (همان امضای فاز ۲۹) بی‌تغییر کار می‌کنند.
            forecast_kwargs: Dict[str, Any] = {}
            if self._range_target_units == "atr":
                forecast_kwargs["atr_reference"] = self._reference_atr(latest_range)
            self._last_range = self._range_predictor.forecast(
                self._range_artifact,
                range_window,
                reference_close=float(latest_range.close.amount),
                generated_at=str(latest_range.open_time),
                **forecast_kwargs,
            )
            self._range_predictions += 1
        except Exception as error:
            self._last_error = f"range inference failed: {type(error).__name__}: {error}"
            key = f"range: {type(error).__name__}: {str(error)[:80]}"
            self._error_counts[key] = self._error_counts.get(key, 0) + 1
            self._last_range = None
        return self._last_value

    def _ema(self, values: Sequence[float], period: int) -> float:
        """EMA علوی با seed از اولین قیمت (دترمینیستیک، بدون lookahead)."""
        alpha = 2.0 / (period + 1.0)
        result = float(values[0])
        for value in values[1:]:
            result = alpha * float(value) + (1.0 - alpha) * result
        return result

    def _trend_blocks_signal(self, signal: Any) -> tuple[bool, str]:
        """True وقتی جهت سیگنال خلاف ترند EMA50 روزانه است (فاز ۹۶-ب)."""
        candles = list(self._range_candles)
        period = 50
        if len(candles) < period:
            return False, ""
        closes = [float(candle.close.amount) for candle in candles]
        ema = self._ema(closes, period)
        last_close = closes[-1]
        direction = signal.predicted_class.label
        if direction == "sell" and last_close > ema:
            return True, (
                f"trend ema50: SHORT blocked — close {last_close:.2f} > "
                f"EMA50 {ema:.2f} (uptrend)"
            )
        if direction == "buy" and last_close < ema:
            return True, (
                f"trend ema50: LONG blocked — close {last_close:.2f} < "
                f"EMA50 {ema:.2f} (downtrend)"
            )
        return False, ""

    def _daily_context(self) -> tuple[Optional[RangeForecast], Optional[Candle]]:
        """پیش‌بینی D1 + کندل D0 — کش per-day (ورودی در طول روز ثابت است)."""
        if not self._daily_feed:
            return None, None
        d0 = self._daily_feed[-1]
        key = d0.open_time.value
        if self._daily_cache_key == key:
            return self._daily_cache_value, d0

        window = self._daily_window_cache.get(key)
        if window is None:
            window = self._build_window(
                list(self._daily_feed),
                self._daily_timeframe,
                None,
                self._daily_window_size,
                matrix=self._daily_matrix,
                original_index=self._daily_candle_index.get(key),
                model_role="range",
            )
            if window is None:
                return None, None
            self._daily_window_cache[key] = window

        try:
            from ShadBotTrader.infrastructure.ai.target_builder import atr_from_candles

            atr_value = atr_from_candles(list(self._daily_feed), period=14)
        except ValidationError:
            atr_value = None
        try:
            forecast = self._daily_predictor.forecast(
                self._daily_artifact,
                window,
                reference_close=float(d0.close.amount),
                generated_at=str(d0.open_time),
                atr_reference=float(atr_value) if atr_value else None,
            )
        except TypeError:
            # پیش‌بینی‌کنندهٔ با امضای قدیمی (بدون atr_reference)
            forecast = self._daily_predictor.forecast(
                self._daily_artifact,
                window,
                reference_close=float(d0.close.amount),
                generated_at=str(d0.open_time),
            )
        except Exception:
            return None, None
        self._daily_cache_key = key
        self._daily_cache_value = forecast
        return forecast, d0

    def _today_signal_candles(self, day_value: Any) -> List[Candle]:
        """کندل‌های 5M بستهٔ «همان روز» تصمیم (برای fallback دوم SL)."""
        return [
            candle
            for candle in self._signal_candles
            if str(candle.open_time.value)[:10] == str(day_value)[:10]
        ]

    def _triple_bracket(
        self,
        event: MarketEvent,
        side: OrderSide,
        entry_reference: Price,
    ) -> Optional[TradeBracket]:
        """براکت سه‌تایم‌فریمی (فاز ۹۷).

        TP/SL از پیش‌بینی کندل 4H بعدی؛ fallback اول: Low/High روز D0؛
        fallback دوم: کمترین Low زیر ورود (خرید) از کندل‌های 5M امروز
        منهای اسپرد / بیشترین High بالای ورود (فروش) به‌علاوهٔ اسپرد.
        """
        range_fc = self._last_range
        d0 = self._last_d0
        if range_fc is None or d0 is None or event.candle is None:
            return None
        entry = float(entry_reference.amount)
        spread_abs = Decimal("0")
        if self._spread_pct_val:
            spread_abs = Decimal(str(float(entry) * float(self._spread_pct_val)))

        is_buy = side is OrderSide.BUY
        tp = range_fc.predicted_high if is_buy else range_fc.predicted_low
        sl = range_fc.predicted_low if is_buy else range_fc.predicted_high

        # fallback 1 — D0
        if is_buy and sl >= entry:
            sl = float(d0.low.amount)
            self._sl_fallback_d0 += 1
        if not is_buy and sl <= entry:
            sl = float(d0.high.amount)
            self._sl_fallback_d0 += 1

        # fallback 2 — کندل‌های 5M امروز
        if is_buy and sl >= entry:
            lows = [
                float(c.low.amount)
                for c in self._today_signal_candles(event.candle.open_time.value)
                if float(c.low.amount) < entry
            ]
            if not lows:
                self._no_sl_found += 1
                return None
            sl = min(lows) - float(spread_abs)
            self._sl_fallback_today += 1
        if not is_buy and sl <= entry:
            highs = [
                float(c.high.amount)
                for c in self._today_signal_candles(event.candle.open_time.value)
                if float(c.high.amount) > entry
            ]
            if not highs:
                self._no_sl_found += 1
                return None
            sl = max(highs) + float(spread_abs)
            self._sl_fallback_today += 1

        # مجوز ۳ — سمت TP
        if is_buy and tp <= entry:
            self._license3_refused += 1
            return None
        if not is_buy and tp >= entry:
            self._license3_refused += 1
            return None

        # R/R (فیلد GUI — اپراتور خواست اعمال بماند)
        multiplier = self._reward_risk_multiplier
        if multiplier:
            tp_dist = abs(tp - entry)
            sl_dist = abs(entry - sl)
            if sl_dist <= 0 or tp_dist < multiplier * sl_dist:
                self._rr_refused += 1
                return None

        try:
            return TradeBracket(
                side=side,
                entry_reference=entry_reference,
                take_profit=Price(Decimal(str(tp))),
                stop_loss=Price(Decimal(str(sl))),
                created_at=event.event_time,
                model_high=Price(Decimal(str(range_fc.predicted_high))),
                model_low=Price(Decimal(str(range_fc.predicted_low))),
                model_reference=Price(Decimal(str(range_fc.reference_close))),
                recentered=(self._sl_fallback_d0 + self._sl_fallback_today) > 0,
            )
        except ValidationError:
            return None

    def _reference_atr(self, latest_range: Candle) -> Optional[float]:
        """ATR(period) at the latest closed range candle (فاز ۹۵).

        Only ATR-unit models need it; for them it de-normalizes the
        forecast back into dollars. Computed causally over the already
        delivered range candles — never a future one — and memoized per
        range bar because several 5M events share one range candle.
        """
        if self._range_target_units != "atr":
            return None
        key = latest_range.open_time.value
        if self._atr_cache_key == key:
            return self._atr_cache_value
        candles = list(self._range_candles)
        if len(candles) < 2:
            return None
        from ShadBotTrader.infrastructure.ai.target_builder import atr_from_candles

        value = atr_from_candles(candles, period=14)
        value = float(value) if value is not None else 0.0
        self._atr_cache_key = key
        self._atr_cache_value = value
        return value if value > 0 else None

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
        self._atr_cache_key = None
        self._atr_cache_value = 0.0
        self._trend_blocks = 0
        self._last_trend_block = ""
        self._last_daily = None
        self._last_d0 = None
        self._daily_cache_key = None
        self._daily_cache_value = None
        self._daily_window_cache = {}
        self._daily_predictions = 0
        self._daily_blocked = 0
        self._sl_fallback_d0 = 0
        self._sl_fallback_today = 0
        self._license3_refused = 0
        self._rr_refused = 0
        self._no_sl_found = 0
        self._daily_feed.clear()
        self._daily_cursor = 0

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

        فاز ۹۷: حالت سه‌تایم‌فریمی (مدل روزانه تنظیم شده باشد) →
        براکت از 4H + fallback های روزانه ساخته می‌شود.
        """
        if self._daily_predictor is not None:
            return self._triple_bracket(event, side, entry_reference)
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
