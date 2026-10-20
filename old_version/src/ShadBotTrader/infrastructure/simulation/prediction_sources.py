"""Prediction sources for simulations (Phase 16, sections 10-11).

A backtest needs predictions without necessarily loading a TensorFlow
model, so the source is abstract. Both implementations here are
deterministic — the same event always yields the same prediction, which
is what keeps a run reproducible.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Dict, Optional

from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.simulation.market_event import MarketEvent
from ShadBotTrader.domain.simulation.ports import PredictionSource


class MomentumPredictionSource(PredictionSource):
    """A transparent momentum rule used as a baseline.

    Compares each close with the close ``lookback`` bars earlier and
    maps the relative change onto ``[0, 1]``. It is intentionally simple:
    the point of a baseline is that its behaviour is obvious, so any
    backtest result can be attributed to the pipeline rather than to a
    black box.

    Strictly causal — only closes at or before the current bar are read.
    """

    def __init__(
        self,
        lookback: int = 3,
        sensitivity: Decimal = Decimal("200"),
        base_confidence: float = 0.75,
    ) -> None:
        if lookback < 1:
            raise ValidationError("lookback must be >= 1")
        if sensitivity <= 0:
            raise ValidationError("sensitivity must be positive")
        if not 0.0 <= base_confidence <= 1.0:
            raise ValidationError("base_confidence must be in [0, 1]")

        self._lookback = lookback
        self._sensitivity = sensitivity
        self._base_confidence = base_confidence
        self._closes: list[Decimal] = []
        self._last_strength: Decimal = Decimal("0")

    def observe(self, event: MarketEvent) -> None:
        """Record the bar. Must be called once per event, in order."""
        if event.candle is not None:
            self._closes.append(event.candle.close.amount)

    def predict(self, event: MarketEvent) -> Optional[float]:
        if len(self._closes) <= self._lookback:
            return None  # not enough history yet

        current = self._closes[-1]
        previous = self._closes[-1 - self._lookback]
        if previous == 0:
            return None

        change = (current - previous) / previous
        # map the change onto [0, 1] around a neutral 0.5
        raw = Decimal("0.5") + change * self._sensitivity
        bounded = min(max(raw, Decimal("0")), Decimal("1"))
        self._last_strength = abs(bounded - Decimal("0.5")) * Decimal("2")
        return float(bounded)

    def confidence(self, event: MarketEvent) -> float:
        """Confidence grows with the strength of the move."""
        scaled = Decimal(str(self._base_confidence)) + self._last_strength * Decimal("0.2")
        return float(min(scaled, Decimal("1")))

    def reset(self) -> None:
        self._closes.clear()
        self._last_strength = Decimal("0")


class ScriptedPredictionSource(PredictionSource):
    """Returns predictions from a fixed schedule, keyed by bar index.

    Useful for tests and what-if scenarios where the exact sequence of
    model outputs must be controlled.
    """

    def __init__(
        self,
        values: Dict[int, float],
        confidences: Optional[Dict[int, float]] = None,
        default_confidence: float = 0.9,
    ) -> None:
        self._values = dict(values)
        self._confidences = dict(confidences or {})
        self._default_confidence = default_confidence
        self._index = -1

    def observe(self, event: MarketEvent) -> None:
        self._index += 1

    def predict(self, event: MarketEvent) -> Optional[float]:
        return self._values.get(self._index)

    def confidence(self, event: MarketEvent) -> float:
        return self._confidences.get(self._index, self._default_confidence)

    def reset(self) -> None:
        self._index = -1
