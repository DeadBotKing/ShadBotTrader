"""Prediction targets of the dual-model architecture (Phase 29).

Two models, two questions:

* the **range model** asks how far price may travel — a regression onto
  the highest high and the lowest low of the next N candles;
* the **signal model** asks what to do about it — a three-way
  classification (sell / hold / buy) carrying its probabilities.

Both targets are expressed as a *fraction of the current close* rather
than an absolute price (Phase 29 §2.1). Gold at 2000 and gold at 3000
are then the same problem; a model trained on absolute levels silently
stops working the moment the market leaves its training range.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional, Tuple

from ShadBotTrader.domain.common.errors import ValidationError


class TargetKind(str, Enum):
    """What a model is trained to output."""

    #: Two continuous offsets: future high and future low.
    PRICE_RANGE = "price_range"
    #: Three probabilities: sell / hold / buy.
    TRADE_SIGNAL = "trade_signal"


class SignalClass(int, Enum):
    """The three mutually exclusive signal labels.

    Ordered so the integer value doubles as the softmax column index:
    ``0 = sell``, ``1 = hold``, ``2 = buy``.

    HOLD exists deliberately. A binary up/down model is forced to take a
    side on every bar, including the majority of bars where nothing
    happens; "no trade" is the most valuable thing a trading model can
    say.
    """

    SELL = 0
    HOLD = 1
    BUY = 2

    @property
    def label(self) -> str:
        return self.name.lower()

    @classmethod
    def from_index(cls, index: int) -> "SignalClass":
        try:
            return cls(index)
        except ValueError as exc:
            raise ValidationError(f"Unknown signal class index: {index}") from exc


@dataclass(frozen=True)
class PredictionTarget:
    """Declares what a model predicts and how far ahead.

    ``horizon`` is counted in candles of the model's own timeframe, so a
    horizon of 5 on 1H bars means the next five hours.
    """

    kind: TargetKind
    horizon: int
    timeframe: str
    #: Neutral band for the signal model, as a price fraction.
    threshold: float = 0.0008

    def __post_init__(self) -> None:
        if self.horizon < 1:
            raise ValidationError("horizon must be >= 1 candle")
        if not self.timeframe.strip():
            raise ValidationError("timeframe must not be empty")
        if self.kind is TargetKind.TRADE_SIGNAL and self.threshold <= 0:
            raise ValidationError(
                "A signal threshold must be positive: a zero band would "
                "label pure noise as a tradable move."
            )

    @property
    def output_units(self) -> int:
        """Width of the model's output layer."""
        return 2 if self.kind is TargetKind.PRICE_RANGE else 3

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

    The offsets are fractions of ``reference_close``; the absolute
    prices are derived, never stored twice.
    """

    reference_close: float
    high_offset: float
    low_offset: float
    horizon: int
    timeframe: str = ""
    generated_at: str = ""

    def __post_init__(self) -> None:
        if self.reference_close <= 0:
            raise ValidationError("reference_close must be positive")

    @property
    def predicted_high(self) -> float:
        return self.reference_close * (1.0 + self.high_offset)

    @property
    def predicted_low(self) -> float:
        return self.reference_close * (1.0 + self.low_offset)

    @property
    def expected_range(self) -> float:
        """Predicted high minus predicted low, in price units."""
        return self.predicted_high - self.predicted_low

    @property
    def is_coherent(self) -> bool:
        """False when the model predicted a high below its own low.

        A regression head has no structural guarantee that one output
        stays above the other. Reporting the incoherence is honest;
        silently swapping the two would hide a broken model.
        """
        return self.predicted_high >= self.predicted_low

    @property
    def upside(self) -> float:
        """Distance from the current close up to the predicted high."""
        return self.predicted_high - self.reference_close

    @property
    def downside(self) -> float:
        """Distance from the current close down to the predicted low."""
        return self.reference_close - self.predicted_low

    def reward_risk(self) -> Optional[float]:
        """Upside divided by downside, or None when downside is zero.

        ``None`` means undefined, not infinite and not zero: with no
        predicted downside there is no ratio to report.
        """
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
        }


@dataclass(frozen=True)
class SignalForecast:
    """A directional call with the probability behind it.

    This is the object that answers "90% chance it should be a buy": the
    whole softmax vector is preserved rather than collapsed to a single
    number, because the distance between 0.90 and 0.34 is the entire
    decision.
    """

    sell_probability: float
    hold_probability: float
    buy_probability: float
    horizon: int
    timeframe: str = ""
    generated_at: str = ""

    def __post_init__(self) -> None:
        for name, value in (
            ("sell", self.sell_probability),
            ("hold", self.hold_probability),
            ("buy", self.buy_probability),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValidationError(f"{name}_probability must be in [0, 1], got {value}")
        total = self.sell_probability + self.hold_probability + self.buy_probability
        if abs(total - 1.0) > 0.02:
            raise ValidationError(f"Signal probabilities must sum to 1.0, got {total:.4f}")

    @classmethod
    def from_vector(
        cls,
        probabilities: Tuple[float, float, float],
        horizon: int,
        timeframe: str = "",
        generated_at: str = "",
    ) -> "SignalForecast":
        """Build from a softmax vector ordered ``(sell, hold, buy)``."""
        sell, hold, buy = probabilities
        return cls(
            sell_probability=float(sell),
            hold_probability=float(hold),
            buy_probability=float(buy),
            horizon=horizon,
            timeframe=timeframe,
            generated_at=generated_at,
        )

    @property
    def probabilities(self) -> Tuple[float, float, float]:
        return (self.sell_probability, self.hold_probability, self.buy_probability)

    @property
    def predicted_class(self) -> SignalClass:
        """The most likely class — even when that class is HOLD."""
        best = max(range(3), key=lambda index: self.probabilities[index])
        return SignalClass.from_index(best)

    @property
    def confidence(self) -> float:
        """Probability of the winning class, in [0, 1]."""
        return max(self.probabilities)

    @property
    def directional_confidence(self) -> float:
        """How strongly the model prefers buy over sell, ignoring hold.

        Renormalises the two directional classes against each other, so
        a 0.45/0.10/0.45 split reads as genuinely undecided rather than
        as a weak buy.
        """
        directional = self.sell_probability + self.buy_probability
        if directional <= 0:
            return 0.5
        return self.buy_probability / directional

    def is_actionable(self, minimum: float = 0.6) -> bool:
        """True when a *directional* class wins by at least ``minimum``.

        HOLD winning is a valid, common and useful outcome — but it is
        not something to trade on.
        """
        if self.predicted_class is SignalClass.HOLD:
            return False
        return self.confidence >= minimum

    def describe(self) -> str:
        """One human-readable line, e.g. ``buy 90.0%``."""
        return f"{self.predicted_class.label} {self.confidence * 100:.1f}%"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sell_probability": self.sell_probability,
            "hold_probability": self.hold_probability,
            "buy_probability": self.buy_probability,
            "predicted_class": self.predicted_class.label,
            "confidence": self.confidence,
            "directional_confidence": self.directional_confidence,
            "actionable": self.is_actionable(),
            "horizon": self.horizon,
            "timeframe": self.timeframe,
            "generated_at": self.generated_at,
        }
