"""Prediction targets of the dual-model architecture.

The range model is a two-output regression (future high and low).  The
signal model is deliberately binary: it predicts only SELL or BUY.  HOLD
is not a model class; the strategy may still return a HOLD decision when a
probability threshold, range check or risk rule says not to trade.

Price-range targets are expressed as dimensionless offsets rather than
absolute prices: fractions of the current close for legacy ``"pct"``
models, ATR multiples for the فاز ۹۵ ``"atr"`` models (the pct target
made every prediction collapse to one constant percentage; see
``docs/Report/PHASE95_REPORT.md``).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Sequence, Tuple

from ShadBotTrader.domain.common.errors import ValidationError


class TargetKind(str, Enum):
    """What a model is trained to output."""

    PRICE_RANGE = "price_range"
    TRADE_SIGNAL = "trade_signal"


class SignalClass(int, Enum):
    """The two mutually exclusive signal labels.

    The integer values are the softmax column indices:
    ``0 = sell`` and ``1 = buy``.  There is intentionally no HOLD output.
    """

    SELL = 0
    BUY = 1

    @property
    def label(self) -> str:
        return self.name.lower()

    @classmethod
    def from_index(cls, index: int) -> "SignalClass":
        try:
            return cls(index)
        except ValueError as exc:
            raise ValidationError(
                f"Unknown binary signal class index: {index}; expected 0 (sell) or 1 (buy)"
            ) from exc


@dataclass(frozen=True)
class PredictionTarget:
    """Declares what a model predicts and how far ahead.

    For the binary signal model, ``threshold`` is the minimum price move
    used by the first-passage labeler. A signal horizon of ``0`` means
    search forward until BUY or SELL threshold is hit.
    """

    kind: TargetKind
    horizon: int
    timeframe: str
    threshold: float = 0.0008

    def __post_init__(self) -> None:
        if self.horizon < 0 or (self.kind is TargetKind.PRICE_RANGE and self.horizon < 1):
            raise ValidationError("horizon must be >= 1 for range and >= 0 for signal")
        if not self.timeframe.strip():
            raise ValidationError("timeframe must not be empty")
        if self.kind is TargetKind.TRADE_SIGNAL and self.threshold <= 0:
            raise ValidationError("binary signal threshold must be positive")
        if self.threshold < 0:
            raise ValidationError("threshold must not be negative")

    @property
    def output_units(self) -> int:
        """Width of the model output layer."""
        return 2

    @property
    def is_regression(self) -> bool:
        return self.kind is TargetKind.PRICE_RANGE

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind.value,
            "horizon": self.horizon,
            "timeframe": self.timeframe,
            "threshold": self.threshold,
            "output_units": self.output_units,
        }


@dataclass(frozen=True)
class RangeForecast:
    """Predicted price extremes over the horizon.

    ``target_units`` declares how ``high_offset``/``low_offset`` read:

    * ``"pct"`` (legacy) — fractions of ``reference_close``;
      ``predicted_high = reference_close · (1 + high_offset)``.
    * ``"atr"`` (فاز ۹۵) — ATR multiples;
      ``predicted_high = reference_close + high_atr_mult · atr_reference``.
      ``high_offset`` is kept in sync as the equivalent fraction so every
      existing percent display stays honest.

    The ATR conversion happens once, here and in the predictor — every
    consumer (bracket, backtest, strategy, GUI) keeps reading absolute
    prices and never needs to know the model's target units.
    """

    reference_close: float
    high_offset: float
    low_offset: float
    horizon: int
    timeframe: str = ""
    generated_at: str = ""
    target_units: str = "pct"
    #: ATR(period) at the reference candle; only meaningful for "atr".
    atr_reference: float = 0.0
    high_atr_mult: float = 0.0
    low_atr_mult: float = 0.0

    def __post_init__(self) -> None:
        if self.reference_close <= 0:
            raise ValidationError("reference_close must be positive")
        if self.target_units not in ("pct", "atr"):
            raise ValidationError(
                f"Unknown range target units: {self.target_units!r} (use 'pct' or 'atr')"
            )
        if self.target_units == "atr" and self.atr_reference <= 0:
            raise ValidationError(
                "An ATR-unit forecast needs a positive atr_reference; without "
                "it the ATR multiples cannot be turned into prices"
            )

    @property
    def predicted_high(self) -> float:
        if self.target_units == "atr":
            return self.reference_close + self.high_atr_mult * self.atr_reference
        return self.reference_close * (1.0 + self.high_offset)

    @property
    def predicted_low(self) -> float:
        if self.target_units == "atr":
            return self.reference_close + self.low_atr_mult * self.atr_reference
        return self.reference_close * (1.0 + self.low_offset)

    @property
    def expected_range(self) -> float:
        return self.predicted_high - self.predicted_low

    @property
    def is_coherent(self) -> bool:
        """False when the model predicted a high below its low."""
        return self.predicted_high >= self.predicted_low

    @property
    def upside(self) -> float:
        return self.predicted_high - self.reference_close

    @property
    def downside(self) -> float:
        return self.reference_close - self.predicted_low

    def reward_risk(self) -> Optional[float]:
        if self.downside <= 0:
            return None
        return self.upside / self.downside

    def to_dict(self) -> Dict[str, Any]:
        return {
            "reference_close": self.reference_close,
            "high_offset": self.high_offset,
            "low_offset": self.low_offset,
            "predicted_high": self.predicted_high,
            "predicted_low": self.predicted_low,
            "expected_range": self.expected_range,
            "upside": self.upside,
            "downside": self.downside,
            "reward_risk": self.reward_risk(),
            "coherent": self.is_coherent,
            "horizon": self.horizon,
            "timeframe": self.timeframe,
            "generated_at": self.generated_at,
            "target_units": self.target_units,
            "atr_reference": self.atr_reference,
            "high_atr_mult": self.high_atr_mult,
            "low_atr_mult": self.low_atr_mult,
        }


@dataclass(frozen=True)
class SignalForecast:
    """A binary SELL/BUY probability forecast.

    ``sell_probability`` and ``buy_probability`` sum to one.  A low
    winning probability is handled by the strategy's configurable
    confidence gate; it is not converted into a third HOLD class.
    """

    sell_probability: float
    buy_probability: float
    horizon: int
    timeframe: str = ""
    generated_at: str = ""

    def __post_init__(self) -> None:
        for name, value in (
            ("sell", self.sell_probability),
            ("buy", self.buy_probability),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"{name}_probability must be in [0, 1], got {value}")
        total = self.sell_probability + self.buy_probability
        if abs(total - 1.0) > 0.02:
            raise ValidationError(f"Binary signal probabilities must sum to 1.0, got {total:.4f}")

    @classmethod
    def from_vector(
        cls,
        probabilities: Sequence[float],
        horizon: int,
        timeframe: str = "",
        generated_at: str = "",
    ) -> "SignalForecast":
        """Build from a binary vector ordered ``(sell, buy)``.

        A three-value vector is rejected explicitly so a stale HOLD model
        cannot silently enter the new binary trading pipeline.
        """
        if len(probabilities) != 2:
            raise ValidationError(
                "The binary signal model must provide exactly 2 probabilities "
                "(sell, buy); HOLD is not a model class."
            )
        sell, buy = probabilities
        return cls(
            sell_probability=float(sell),
            buy_probability=float(buy),
            horizon=horizon,
            timeframe=timeframe,
            generated_at=generated_at,
        )

    @property
    def probabilities(self) -> Tuple[float, float]:
        return (self.sell_probability, self.buy_probability)

    @property
    def predicted_class(self) -> SignalClass:
        best = max(range(2), key=lambda index: self.probabilities[index])
        return SignalClass.from_index(best)

    @property
    def confidence(self) -> float:
        return max(self.probabilities)

    @property
    def directional_confidence(self) -> float:
        """BUY probability on the binary directional axis."""
        total = self.sell_probability + self.buy_probability
        return 0.5 if total <= 0 else self.buy_probability / total

    def is_actionable(self, minimum: float = 0.6) -> bool:
        """True when the winning BUY/SELL probability clears ``minimum``."""
        return self.confidence >= minimum

    def describe(self) -> str:
        return f"{self.predicted_class.label} {self.confidence * 100:.1f}%"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sell_probability": self.sell_probability,
            "buy_probability": self.buy_probability,
            "predicted_class": self.predicted_class.label,
            "confidence": self.confidence,
            "directional_confidence": self.directional_confidence,
            "actionable": self.is_actionable(),
            "horizon": self.horizon,
            "timeframe": self.timeframe,
            "generated_at": self.generated_at,
        }
