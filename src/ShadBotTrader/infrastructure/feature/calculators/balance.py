"""Candle balance features: color, extension and power (ported from legacy)."""

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


def _color_series(frame: pd.DataFrame) -> pd.Series:
    """1 for a bullish (green) candle, 0 for a bearish (red) candle."""
    return (frame["close"] >= frame["open"]).astype(float)


def _extension_for_color(frame: pd.DataFrame, color: pd.Series, value: int) -> pd.Series:
    """Volume/price extension ratio versus the previous same-color candle.

    Only candles of the requested color get a value; every other candle is
    zero. ``inf`` is replaced by 1 and ``-inf`` by -1 (legacy behaviour).
    """
    mask = (color == value).to_numpy()
    close = frame["close"]
    volume = frame["volume"]

    price_ratio = pd.Series(np.nan, index=frame.index)
    volume_ratio = pd.Series(np.nan, index=frame.index)

    color_close = close[mask]
    color_volume = volume[mask]
    if len(color_close) > 1:
        prev_close = color_close.shift(1)
        prev_volume = color_volume.shift(1)
        price_ratio.loc[mask] = (color_close - prev_close) / ((color_close + prev_close) / 2.0)
        volume_ratio.loc[mask] = (color_volume - prev_volume) / ((color_volume + prev_volume) / 2.0)

    extension = volume_ratio / price_ratio.replace(0.0, np.nan)
    extension = extension.fillna(0.0)
    extension = extension.replace(np.inf, 1.0).replace(-np.inf, -1.0)
    return extension.fillna(0.0)


def _power_for_color(frame: pd.DataFrame, color: pd.Series, value: int) -> pd.Series:
    """Body-to-wick power ratio for candles of one color (legacy ``power``)."""
    mask = (color == value).to_numpy()
    body = (frame["close"] - frame["open"]).abs()
    wick = (frame["high"] - frame["low"] - body).abs()

    power = pd.Series(0.0, index=frame.index)
    ratio = (body / wick.replace(0.0, np.nan)).where(mask, 0.0)
    ratio = ratio.fillna(0.0).replace(np.inf, 1.0).replace(-np.inf, 0.0)
    power.loc[:] = ratio.fillna(0.0)
    return power


class BalanceCalculator(FeatureCalculator):
    """Computes color_candle / extension_{green,red} / power_{green,red}.

    Parameters:
        ``kind`` — one of ``color``, ``extension``, ``power``.
        ``color`` — for extension/power: ``green`` or ``red``.
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        kind = str(definition.parameters["kind"])
        frame = candle_frame(context)
        color = _color_series(frame)

        if kind == "color":
            values = color
        elif kind == "extension":
            value = 1 if definition.parameters["color"] == "green" else 0
            values = _extension_for_color(frame, color, value)
        else:  # power
            value = 1 if definition.parameters["color"] == "green" else 0
            values = _power_for_color(frame, color, value)

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=0,
        )
