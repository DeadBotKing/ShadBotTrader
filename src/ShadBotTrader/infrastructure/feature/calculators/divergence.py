"""Classic price/oscillator divergence detector (causal)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)

_EXTREME_ORDER = 5


def _indicator_series(frame: pd.DataFrame, indicator: str) -> pd.Series:
    """Compute the oscillator series for the requested indicator family."""
    close = frame["close"]
    if indicator == "rsi":
        period = 14
        delta = close.diff()
        gain = delta.clip(lower=0.0)
        loss = -delta.clip(upper=0.0)
        avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
        avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
        return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss.replace(0.0, 1e-12))

    if indicator in ("macd", "macds", "macdh"):
        ema_fast = close.ewm(span=12, adjust=False, min_periods=12).mean()
        ema_slow = close.ewm(span=26, adjust=False, min_periods=26).mean()
        macd_line = ema_fast - ema_slow
        signal_line = macd_line.ewm(span=9, adjust=False, min_periods=9).mean()
        if indicator == "macd":
            return macd_line
        if indicator == "macds":
            return signal_line
        return macd_line - signal_line

    # stochastic %K / %D
    period = 14
    lowest_low = frame["low"].rolling(period, min_periods=period).min()
    highest_high = frame["high"].rolling(period, min_periods=period).max()
    percent_k = 100.0 * (close - lowest_low) / (highest_high - lowest_low).replace(0.0, 1e-12)
    if indicator == "stoch_k":
        return percent_k
    return percent_k.rolling(3, min_periods=3).mean()


def _local_extrema(values: np.ndarray, kind: str) -> list[int]:
    order = _EXTREME_ORDER
    indexes: list[int] = []
    for i in range(order, len(values) - order):
        window = values[i - order : i + order + 1]
        if kind == "min" and values[i] == window.min():
            indexes.append(i)
        elif kind == "max" and values[i] == window.max():
            indexes.append(i)
    return indexes


class DivergenceCalculator(FeatureCalculator):
    """Detects classic divergence between price and an oscillator.

    Bullish (buy) divergence: price makes a lower low while the oscillator
    makes a higher low. Bearish (sell): price makes a higher high while
    the oscillator makes a lower high. The result is a boolean series:
    ``1.0`` at candles where divergence is confirmed, ``0.0`` elsewhere.
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        indicator = str(definition.parameters["indicator"])
        signaltype = str(definition.parameters.get("signaltype", "buy"))

        frame = candle_frame(context)
        close = frame["close"].to_numpy(dtype=np.float64)
        oscillator = _indicator_series(frame, indicator).to_numpy(dtype=np.float64)

        signal = np.zeros(len(frame), dtype=np.float64)

        if signaltype == "buy":
            extrema = _local_extrema(close, "min")
            for previous, current in zip(extrema, extrema[1:], strict=False):
                if np.isnan(oscillator[current]) or np.isnan(oscillator[previous]):
                    continue
                if close[current] < close[previous] and oscillator[current] > oscillator[previous]:
                    signal[current] = 1.0
        else:
            extrema = _local_extrema(close, "max")
            for previous, current in zip(extrema, extrema[1:], strict=False):
                if np.isnan(oscillator[current]) or np.isnan(oscillator[previous]):
                    continue
                if close[current] > close[previous] and oscillator[current] < oscillator[previous]:
                    signal[current] = 1.0

        values = pd.Series(signal, index=frame.index)
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=0,
        )
