"""Trend Strength features (causal).

استراتژی Trend Following:
  قوت روند رو اندازه می‌گیریم تا بدونیم کِی سوار روند بشیم.

Features:
  - adx         : Average Directional Index — قوت روند (14)
  - plus_di     : +DI — قوت روند صعودی
  - minus_di    : -DI — قوت روند نزولی
  - di_spread   : +DI - (-DI) — جهت روند خالص
  - ema_cross   : نسبت EMA سریع / EMA کند (> 1 = صعودی)
  - price_vs_ema: فاصله قیمت از EMA به صورت نسبی
"""

from __future__ import annotations

import pandas as pd

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


def _true_range(frame: pd.DataFrame) -> pd.Series:
    prev_close = frame["close"].shift(1)
    return pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - prev_close).abs(),
            (frame["low"] - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _adx_components(frame: pd.DataFrame, period: int):
    """محاسبه ADX، +DI، -DI با روش Wilder (causal)."""
    high = frame["high"]
    low = frame["low"]
    tr = _true_range(frame)

    # Directional Movement
    up_move = high.diff()
    down_move = -low.diff()
    plus_dm = pd.Series(0.0, index=frame.index)
    minus_dm = pd.Series(0.0, index=frame.index)

    plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
    minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[
        (down_move > up_move) & (down_move > 0)
    ]

    # Wilder smoothing
    alpha = 1.0 / period
    atr_s = tr.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    plus_di = 100.0 * plus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr_s.replace(0.0, 1e-12)
    minus_di = 100.0 * minus_dm.ewm(alpha=alpha, adjust=False, min_periods=period).mean() / atr_s.replace(0.0, 1e-12)

    dx = 100.0 * (plus_di - minus_di).abs() / (plus_di + minus_di).replace(0.0, 1e-12)
    adx = dx.ewm(alpha=alpha, adjust=False, min_periods=period).mean()
    return adx, plus_di, minus_di


class TrendStrengthCalculator(FeatureCalculator):
    """محاسبه فیچرهای قوت روند (همه causal).

    پارامترها:
      kind: نوع فیچر — یکی از:
        'adx'         : ADX (شاخص قوت روند، 0-100)
        'plus_di'     : +DI
        'minus_di'    : -DI
        'di_spread'   : +DI - (-DI) (جهت روند)
        'ema_cross'   : EMA سریع / EMA کند
        'price_vs_ema': (close - EMA) / EMA
      period  : دوره ADX (پیش‌فرض 14)
      fast    : دوره EMA سریع (پیش‌فرض 10)
      slow    : دوره EMA کند (پیش‌فرض 30)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "adx"))
        period = int(params.get("period", 14))
        fast = int(params.get("fast", 10))
        slow = int(params.get("slow", 30))

        frame = candle_frame(context)

        if kind in ("adx", "plus_di", "minus_di", "di_spread"):
            adx, plus_di, minus_di = _adx_components(frame, period)
            warmup = period * 2
            if kind == "adx":
                values = adx
            elif kind == "plus_di":
                values = plus_di
            elif kind == "minus_di":
                values = minus_di
            else:  # di_spread
                values = plus_di - minus_di

        elif kind == "ema_cross":
            close = frame["close"]
            ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
            ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
            values = ema_fast / ema_slow.replace(0.0, 1e-12)
            warmup = slow

        elif kind == "price_vs_ema":
            close = frame["close"]
            ema = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
            values = (close - ema) / ema.replace(0.0, 1e-12)
            warmup = slow

        else:
            raise ValueError(f"TrendStrengthCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
