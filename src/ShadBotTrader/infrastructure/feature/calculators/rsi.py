"""Relative Strength Index calculator (Wilder smoothing, causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


class RsiCalculator(FeatureCalculator):
    """Computes ``rsi_{period}`` with Wilder's smoothing (causal)."""

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        frame = candle_frame(context)
        delta = frame["close"].diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)

        avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

        relative_strength = avg_gain / avg_loss.replace(0.0, 1e-12)
        values = 100.0 - (100.0 / (1.0 + relative_strength))

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=period,
        )
