"""Average True Range calculator (Wilder smoothing, causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


class AtrCalculator(FeatureCalculator):
    """Computes ``atr_{period}`` using the true range (causal)."""

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        frame = candle_frame(context)

        previous_close = frame["close"].shift(1)
        true_range = frame[["high", "low"]].join(previous_close.rename("prev_close"))
        true_range = (
            (true_range["high"] - true_range["low"])
            .combine((true_range["high"] - true_range["prev_close"]).abs(), max)
            .combine((true_range["low"] - true_range["prev_close"]).abs(), max)
        )
        values = true_range.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=period,
        )
