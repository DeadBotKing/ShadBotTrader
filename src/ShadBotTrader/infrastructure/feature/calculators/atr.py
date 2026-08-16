"""Average True Range calculator (causal; rma and tr modes)."""

from __future__ import annotations

import pandas as pd

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


def _true_range(frame) -> "pd.Series":
    previous_close = frame["close"].shift(1)
    return pd.concat(
        [
            (frame["high"] - frame["low"]),
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


class AtrCalculator(FeatureCalculator):
    """Computes ATR.

    ``mode`` parameter:

    * ``rma`` (default): Wilder-smoothed true range (standard ATR).
    * ``tr``: the raw true range (legacy ``atr_tr_*`` semantics).
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        period = int(definition.parameters["period"])
        mode = str(definition.parameters.get("mode", "rma"))
        frame = candle_frame(context)
        tr = _true_range(frame)
        if mode == "tr":
            values = tr
            warmup = 1
        else:
            values = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            warmup = period
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
