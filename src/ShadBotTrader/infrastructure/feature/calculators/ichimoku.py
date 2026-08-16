"""Ichimoku Kinko Hyo calculator (causal)."""

from __future__ import annotations

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


class IchimokuCalculator(FeatureCalculator):
    """Computes one Ichimoku line (spana/spanb/tenkan/kijun/chikou).

    Parameters: ``tenkan``, ``kijun``, ``senkou``, and ``line`` selecting
    which of the five lines to emit. ``chikou`` is shifted back by the
    kijun period (as in the legacy implementation).
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        tenkan = int(definition.parameters.get("tenkan", 9))
        kijun = int(definition.parameters.get("kijun", 26))
        senkou = int(definition.parameters.get("senkou", 52))
        line = str(definition.parameters["line"])

        frame = candle_frame(context)
        high = frame["high"]
        low = frame["low"]

        tenkan_sen = (high.rolling(tenkan).max() + low.rolling(tenkan).min()) / 2.0
        kijun_sen = (high.rolling(kijun).max() + low.rolling(kijun).min()) / 2.0
        span_a = ((tenkan_sen + kijun_sen) / 2.0).shift(kijun)
        span_b = ((high.rolling(senkou).max() + low.rolling(senkou).min()) / 2.0).shift(kijun)

        if line == "tenkan":
            values = tenkan_sen
        elif line == "kijun":
            values = kijun_sen
        elif line == "spana":
            values = span_a
        elif line == "spanb":
            values = span_b
        else:  # chikou: close shifted back kijun periods (legacy behaviour)
            values = frame["close"].shift(-kijun)

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=max(kijun, senkou) - 1,
        )
