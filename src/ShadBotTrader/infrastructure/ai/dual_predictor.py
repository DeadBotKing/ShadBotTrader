"""Inference for the two Phase 29 models.

``WavenetPredictor`` returns a single ``Prediction`` with the winning
class and its probability — enough for the original direction model, but
it throws away the rest of the softmax vector. "90% buy" and "40% buy,
35% hold, 25% sell" are very different situations that collapse to the
same answer once the vector is gone.

These predictors keep the full output:

* :class:`RangePredictor`  -> :class:`RangeForecast`  (high/low offsets)
* :class:`SignalPredictor` -> :class:`SignalForecast` (sell/buy probabilities)
"""

from __future__ import annotations

from typing import Any, List, Sequence

from ShadBotTrader.domain.ai.model_artifact import ModelArtifact
from ShadBotTrader.domain.ai.prediction_target import RangeForecast, SignalForecast
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.infrastructure.ai.data_windowing import minmax_scale_window


def _prepare(window: Sequence[Sequence[float]], model: Any) -> Any:
    """Scale a window and shape it into a single-item batch."""
    import numpy as np

    if len(window) == 0:
        raise ValidationError("Inference window is empty")

    scaled = minmax_scale_window([list(row) for row in window])
    x = np.array([scaled], dtype=np.float32)

    expected = getattr(model, "input_shape", None)
    if expected is not None and len(expected) == 3:
        exp_window, exp_features = expected[1], expected[2]
        if exp_window is not None and x.shape[1] != exp_window:
            raise ValidationError(
                f"Window has {x.shape[1]} time steps but the model expects {exp_window}."
            )
        if exp_features is not None and x.shape[2] != exp_features:
            raise ValidationError(
                f"Window has {x.shape[2]} features but the model expects "
                f"{exp_features}. Target columns must be excluded from the input."
            )
    return x


def _load(artifact: ModelArtifact) -> Any:
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
        _deserialize_model,
    )

    return _deserialize_model(artifact.payload)


class RangePredictor:
    """Predicts the future high/low offsets of the next N candles.

    ``target_units`` must match how the model was trained (فاز ۹۵):

    * ``"pct"`` — the output already is a fraction of the close (legacy);
    * ``"atr"`` — the output is an ATR multiple and ``forecast`` needs
      ``atr_reference`` (ATR(period) at the reference candle, computed
      with :func:`wilder_atr_series` on candles up to that candle) to
      turn the multiples into prices. Missing ATR is a hard error: an
      unconvertible forecast must never reach the trading path silently.
    """

    def __init__(
        self,
        horizon: int = 5,
        timeframe: str = "1H",
        target_units: str = "pct",
    ) -> None:
        if target_units not in ("pct", "atr"):
            raise ValidationError(
                f"Unknown range target units: {target_units!r} (use 'pct' or 'atr')"
            )
        self._horizon = horizon
        self._timeframe = timeframe
        self._target_units = target_units
        self._model: Any = None
        self._model_key: Any = None

    @property
    def target_units(self) -> str:
        """The training units this predictor expects ("pct" or "atr")."""
        return self._target_units

    def forecast(
        self,
        artifact: ModelArtifact,
        window: Sequence[Sequence[float]],
        reference_close: float,
        generated_at: str = "",
        atr_reference: Any = None,
    ) -> RangeForecast:
        """Run the range model over one window.

        ``reference_close`` is the close the offsets are measured
        against — the last known price, never a future one.
        ``atr_reference`` (ATR-unit models only) is ATR(period) at the
        reference candle; the forecast's prices become
        ``close + mult × ATR``.
        """
        if reference_close <= 0:
            raise ValidationError("reference_close must be positive")
        if self._target_units == "atr":
            try:
                atr_value = float(atr_reference)
            except (TypeError, ValueError):
                atr_value = 0.0
            if atr_value <= 0:
                raise ValidationError(
                    "This model was trained on ATR-normalized targets, so "
                    "forecast() needs atr_reference = ATR(period) at the "
                    "reference candle; got "
                    f"{atr_reference!r}. Compute it with "
                    "target_builder.atr_from_candles on candles up to and "
                    "including the reference candle."
                )
        else:
            atr_value = 0.0

        key = (artifact.model_id.value, artifact.version.number, artifact.checksum)
        if self._model is None or self._model_key != key:
            self._model = _load(artifact)
            self._model_key = key
        model = self._model
        x = _prepare(window, model)
        raw_out = model.predict(x, verbose=0)

        # فاز ۵۵: seq2seq output shape = [batch, window, horizon*2]
        # scalar output shape = [batch, 2]
        raw = raw_out[0]
        if raw.ndim == 2 and raw.shape[-1] >= 2 and raw.shape[0] > 2:
            # seq2seq: shape=[window, horizon*2]
            # آخرین timestep = پیش‌بینی برای آخرین کندل window
            # layout: [high_1, low_1, high_2, low_2, ..., high_H, low_H]
            last_step = raw[-1]  # [horizon*2]
            n_pairs = len(last_step) // 2

            if n_pairs == 1:
                # horizon=1: دقیقاً high و low فردا
                best_high = float(last_step[0])
                best_low = float(last_step[1])
            else:
                # horizon>1: worst-case high/low در کل افق
                highs = [float(last_step[k * 2]) for k in range(n_pairs)]
                lows = [float(last_step[k * 2 + 1]) for k in range(n_pairs)]
                best_high = max(highs)
                best_low = min(lows)
        elif raw.ndim == 1 and len(raw) >= 2:
            # scalar output (قدیمی)
            best_high = float(raw[0])
            best_low = float(raw[1])
        elif raw.ndim == 2 and raw.shape[0] == 1:
            # [1, 2] شکل قدیمی batch=1
            best_high = float(raw[0, 0])
            best_low = float(raw[0, 1])
        else:
            raise ValidationError(f"Unexpected range model output shape: {raw.shape}")

        # فاز ۹۵: خروجی مدل در units تارگتِ آموزش است. برای مدل ATR،
        # دلار = close + mult × ATR؛ معادل کسریِ close هم ذخیره میشه تا
        # همهٔ نمایش‌های درصدی قدیمی درست بمونن.
        if self._target_units == "atr":
            high_offset = best_high * atr_value / reference_close
            low_offset = best_low * atr_value / reference_close
        else:
            high_offset = best_high
            low_offset = best_low

        return RangeForecast(
            reference_close=float(reference_close),
            high_offset=high_offset,
            low_offset=low_offset,
            horizon=self._horizon,
            timeframe=self._timeframe,
            generated_at=generated_at,
            target_units=self._target_units,
            atr_reference=atr_value if self._target_units == "atr" else 0.0,
            high_atr_mult=best_high if self._target_units == "atr" else 0.0,
            low_atr_mult=best_low if self._target_units == "atr" else 0.0,
        )


class SignalPredictor:
    """Predicts binary sell / buy probabilities."""

    def __init__(self, horizon: int = 5, timeframe: str = "5M") -> None:
        self._horizon = horizon
        self._timeframe = timeframe
        self._model: Any = None
        self._model_key: Any = None

    def forecast(
        self,
        artifact: ModelArtifact,
        window: Sequence[Sequence[float]],
        generated_at: str = "",
    ) -> SignalForecast:
        """Run the signal model over one window, keeping every probability."""
        key = (artifact.model_id.value, artifact.version.number, artifact.checksum)
        if self._model is None or self._model_key != key:
            self._model = _load(artifact)
            self._model_key = key
        model = self._model
        x = _prepare(window, model)
        raw = model.predict(x, verbose=0)[0]

        if len(raw) != 2:
            raise ValidationError(
                f"The binary signal model must emit 2 probabilities "
                f"(sell, buy); got {len(raw)}. HOLD is not supported."
            )

        values: List[float] = [float(value) for value in raw]
        total = sum(values)
        if total <= 0:
            raise ValidationError("The signal model returned a zero probability vector")
        # Guard against tiny softmax drift so the forecast's own
        # validation cannot reject a legitimate model output.
        normalised = [value / total for value in values]

        return SignalForecast.from_vector(
            (normalised[0], normalised[1]),
            horizon=self._horizon,
            timeframe=self._timeframe,
            generated_at=generated_at,
        )
