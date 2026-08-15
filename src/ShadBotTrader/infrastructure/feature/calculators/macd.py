"""MACD calculator (causal)."""

from __future__ import annotations

import pandas as pd

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeaturePoint, FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.domain.market.timestamp import Timestamp
from ShadBotTrader.infrastructure.feature.calculators.base import candle_frame


class MacdCalculator(FeatureCalculator):
    """Computes the MACD line (``macd_{fast}_{slow}_{signal}``, causal).

    The carried value is the MACD line (fast EMA minus slow EMA). The
    signal line and histogram are derived from the same series and are
    not part of this scalar feature.
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        fast = int(definition.parameters["fast"])
        slow = int(definition.parameters["slow"])
        signal_period = int(definition.parameters["signal"])

        frame = candle_frame(context)
        close = frame["close"]
        ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
        ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
        macd_line = ema_fast - ema_slow

        timestamps = [candle.open_time.value for candle in context.candles]
        warmup = slow + signal_period - 2
        points = []
        for index, timestamp in enumerate(timestamps):
            if index < warmup:
                points.append(FeaturePoint(timestamp=Timestamp(timestamp), value=None))
                continue
            macd_value = macd_line.iloc[index]
            if pd.isna(macd_value):
                points.append(FeaturePoint(timestamp=Timestamp(timestamp), value=None))
                continue
            points.append(FeaturePoint(timestamp=Timestamp(timestamp), value=float(macd_value)))
        return FeatureResult(feature_id=definition.feature_id.value, points=points, warmup=warmup)


def macd_full(definition: FeatureDefinition, context: FeatureInputContext):
    """Return (macd, signal, hist) series aligned to the context.

    Helper used by consumers that need the full MACD triple.
    """
    fast = int(definition.parameters["fast"])
    slow = int(definition.parameters["slow"])
    signal_period = int(definition.parameters["signal"])
    frame = candle_frame(context)
    close = frame["close"]
    ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
    ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
    return macd_line, signal_line, macd_line - signal_line
