"""Returns / momentum calculator (any price column, causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    derived_frame,
    result_from_series,
)


class ReturnsCalculator(FeatureCalculator):
    """Computes ``{column}_return_{period}`` (close-to-close ratio, causal)."""

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        column = str(definition.parameters.get("column", "close"))
        frame = derived_frame(context)
        values = frame[column].pct_change(periods=period, fill_method=None)
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=period,
        )
