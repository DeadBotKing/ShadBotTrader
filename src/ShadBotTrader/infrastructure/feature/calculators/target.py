"""Lag/target features: shifted price columns (causal and non-causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    derived_frame,
    result_from_series,
)


class TargetCalculator(FeatureCalculator):
    """Computes ``{column}_target_{period}_{shift}``.

    ``shift < 0`` looks into the past (causal), ``shift > 0`` looks into
    the future (non-causal): the definition's causality flag marks the
    future-looking variants as live-incompatible.
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        column = str(definition.parameters["column"])
        shift = int(definition.parameters.get("shift", -1))

        frame = derived_frame(context)
        # shift<0 -> گذشته (row i ← row i+shift)؛ shift>0 -> آینده
        values = frame[column].shift(periods=-shift)
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=0,
        )
