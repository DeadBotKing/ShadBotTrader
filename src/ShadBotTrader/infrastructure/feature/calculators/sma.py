"""Simple moving average calculator."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


class SmaCalculator(FeatureCalculator):
    """Computes ``sma_{period}`` over the close price (causal)."""

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        frame = candle_frame(context)
        values = frame["close"].rolling(window=period, min_periods=period).mean()
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=period - 1,
        )
