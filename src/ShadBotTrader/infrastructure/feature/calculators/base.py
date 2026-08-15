"""Shared helpers for the pandas-based feature calculators."""

from __future__ import annotations

from typing import List, Optional

import pandas as pd

from ShadBotTrader.domain.feature.feature_result import FeaturePoint, FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureInputContext
from ShadBotTrader.domain.market.timestamp import Timestamp


def candle_frame(context: FeatureInputContext) -> pd.DataFrame:
    """Convert a candle series into an aligned pandas DataFrame."""
    return pd.DataFrame(
        {
            "open_time": [candle.open_time.value for candle in context.candles],
            "open": [float(candle.open.amount) for candle in context.candles],
            "high": [float(candle.high.amount) for candle in context.candles],
            "low": [float(candle.low.amount) for candle in context.candles],
            "close": [float(candle.close.amount) for candle in context.candles],
            "volume": [float(candle.volume) for candle in context.candles],
        }
    )


def result_from_series(
    feature_id: str,
    context: FeatureInputContext,
    values: pd.Series,
    warmup: int,
) -> FeatureResult:
    """Build a FeatureResult aligned with the input candles.

    ``values`` must be a pandas Series indexed positionally 0..n-1 in the
    same order as the input candles. ``None``/NaN entries become
    unavailable points; the leading ``warmup`` entries are forced to be
    unavailable by construction.
    """
    timestamps = [candle.open_time.value for candle in context.candles]
    points: List[FeaturePoint] = []
    for index, timestamp in enumerate(timestamps):
        value: Optional[float]
        if index < warmup:
            value = None
        else:
            raw = values.iloc[index]
            value = None if pd.isna(raw) else float(raw)
        points.append(FeaturePoint(timestamp=Timestamp(timestamp), value=value))
    return FeatureResult(feature_id=feature_id, points=points, warmup=warmup)
