"""Stochastic oscillator calculator (causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


class StochasticCalculator(FeatureCalculator):
    """Computes the stochastic %K (causal, scaled 0..100)."""

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        frame = candle_frame(context)
        lowest_low = frame["low"].rolling(window=period, min_periods=period).min()
        highest_high = frame["high"].rolling(window=period, min_periods=period).max()
        denom = (highest_high - lowest_low).replace(0.0, 1e-12)
        values = 100.0 * (frame["close"] - lowest_low) / denom
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=period - 1,
        )
