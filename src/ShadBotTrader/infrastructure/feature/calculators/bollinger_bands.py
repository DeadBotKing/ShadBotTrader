"""Bollinger Bands calculator: lower / mid / upper (causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    derived_frame,
    result_from_series,
)


class BollingerBandsCalculator(FeatureCalculator):
    """Computes one Bollinger band (lower / mid / upper) over ``column``."""

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        num_std = float(definition.parameters.get("num_std", 2.0))
        band = str(definition.parameters["band"])
        column = str(definition.parameters.get("column", "close"))

        frame = derived_frame(context)
        mean = frame[column].rolling(window=period, min_periods=period).mean()
        std = frame[column].rolling(window=period, min_periods=period).std(ddof=0)

        if band == "lower":
            values = mean - num_std * std
        elif band == "upper":
            values = mean + num_std * std
        else:
            values = mean

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=period - 1,
        )
