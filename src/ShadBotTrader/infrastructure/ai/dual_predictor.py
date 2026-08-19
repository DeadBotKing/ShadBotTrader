"""Inference for the two Phase 29 models.

``WavenetPredictor`` returns a single ``Prediction`` with the winning
class and its probability — enough for the original direction model, but
it throws away the rest of the softmax vector. "90% buy" and "40% buy,
35% hold, 25% sell" are very different situations that collapse to the
same answer once the vector is gone.

These predictors keep the full output:

* :class:`RangePredictor`  -> :class:`RangeForecast`  (high/low offsets)
* :class:`SignalPredictor` -> :class:`SignalForecast` (three probabilities)
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
    """Predicts the future high/low offsets of the next N candles."""

    def __init__(self, horizon: int = 5, timeframe: str = "1H") -> None:
        self._horizon = horizon
        self._timeframe = timeframe
        self._model: Any = None
        self._model_key: Any = None

    def forecast(
        self,
        artifact: ModelArtifact,
        window: Sequence[Sequence[float]],
        reference_close: float,
        generated_at: str = "",
    ) -> RangeForecast:
        """Run the range model over one window.

        ``reference_close`` is the close the offsets are measured
        against — the last known price, never a future one.
        """
        if reference_close <= 0:
            raise ValidationError("reference_close must be positive")

        key = (artifact.model_id.value, artifact.version.number, artifact.checksum)
        if self._model is None or self._model_key != key:
            self._model = _load(artifact)
            self._model_key = key
        model = self._model
        x = _prepare(window, model)
        raw = model.predict(x, verbose=0)[0]

        if len(raw) < 2:
            raise ValidationError(
                f"The range model must emit 2 values (high, low); got {len(raw)}."
            )

        return RangeForecast(
            reference_close=float(reference_close),
            high_offset=float(raw[0]),
            low_offset=float(raw[1]),
            horizon=self._horizon,
            timeframe=self._timeframe,
            generated_at=generated_at,
        )


class SignalPredictor:
    """Predicts sell / hold / buy probabilities."""

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

        if len(raw) != 3:
            raise ValidationError(
                f"The signal model must emit 3 probabilities " f"(sell, hold, buy); got {len(raw)}."
            )

        values: List[float] = [float(value) for value in raw]
        total = sum(values)
        if total <= 0:
            raise ValidationError("The signal model returned a zero probability vector")
        # Guard against tiny softmax drift so the forecast's own
        # validation cannot reject a legitimate model output.
        normalised = [value / total for value in values]

        return SignalForecast.from_vector(
            (normalised[0], normalised[1], normalised[2]),
            horizon=self._horizon,
            timeframe=self._timeframe,
            generated_at=generated_at,
        )
