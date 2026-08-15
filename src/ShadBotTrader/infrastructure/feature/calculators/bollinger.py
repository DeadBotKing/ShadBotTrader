"""Bollinger Bands calculator (causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


class BollingerCalculator(FeatureCalculator):
    """Computes the Bollinger %B position (causal, scaled 0..1)."""

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        num_std = float(definition.parameters["num_std"])
        frame = candle_frame(context)
        close = frame["close"]
        mean = close.rolling(window=period, min_periods=period).mean()
        std = close.rolling(window=period, min_periods=period).std(ddof=0)
        upper = mean + num_std * std
        lower = mean - num_std * std
        width = (upper - lower).replace(0.0, 1e-12)
        percent_b = (close - lower) / width
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=percent_b,
            warmup=period - 1,
        )
