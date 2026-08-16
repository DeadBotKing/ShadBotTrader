"""Exponential moving average calculator (any price column, causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    derived_frame,
    result_from_series,
)


class EmaCalculator(FeatureCalculator):
    """Computes ``ema_{period}`` over a configurable price column."""

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        column = str(definition.parameters.get("column", "close"))
        frame = derived_frame(context)
        values = frame[column].ewm(span=period, adjust=False, min_periods=period).mean()
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=period - 1,
        )
