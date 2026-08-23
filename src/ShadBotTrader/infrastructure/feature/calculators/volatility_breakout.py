"""Volatility Breakout features (causal).

استراتژی Volatility Breakout:
  وقتی بازار در حالت فشرده (squeeze) قرار داره،
  انتظار انفجار قیمت رو داریم.

Features:
  - atr_ratio: نسبت ATR کوتاه‌مدت به بلندمدت (مقایسه volatility)
  - bb_squeeze: آیا باندهای Bollinger داخل کانال Keltner هستن؟ (0/1)
  - bb_width: عرض نسبی باند Bollinger به قیمت
  - keltner_width: عرض نسبی کانال Keltner به قیمت
  - squeeze_intensity: شدت فشردگی (هرچه منفی‌تر = squeeze قوی‌تر)
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


class VolatilityBreakoutCalculator(FeatureCalculator):
    """محاسبه فیچرهای Volatility Breakout (همه causal).

    پارامترها (در parameters دیکشنری):
      kind: نوع فیچر — یکی از:
        'atr_ratio'        : نسبت ATR(5) / ATR(20)
        'bb_squeeze'       : آیا BB داخل Keltner هست؟ (0/1)
        'bb_width'         : عرض Bollinger / قیمت
        'keltner_width'    : عرض Keltner / قیمت
        'squeeze_intensity': شدت squeeze (bb_width - keltner_width)
      bb_period  : دوره Bollinger (پیش‌فرض 20)
      bb_std     : انحراف معیار Bollinger (پیش‌فرض 2.0)
      kc_period  : دوره Keltner (پیش‌فرض 20)
      kc_mult    : ضریب ATR در Keltner (پیش‌فرض 1.5)
      atr_fast   : دوره ATR سریع برای atr_ratio (پیش‌فرض 5)
      atr_slow   : دوره ATR کند برای atr_ratio (پیش‌فرض 20)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "bb_squeeze"))
        bb_period = int(params.get("bb_period", 20))
        bb_std = float(params.get("bb_std", 2.0))
        kc_period = int(params.get("kc_period", 20))
        kc_mult = float(params.get("kc_mult", 1.5))
        atr_fast = int(params.get("atr_fast", 5))
        atr_slow = int(params.get("atr_slow", 20))

        frame = candle_frame(context)
        tr = _true_range(frame)

        # --- Bollinger Bands ---
        close = frame["close"]
        bb_mid = close.rolling(bb_period, min_periods=bb_period).mean()
        bb_std_series = close.rolling(bb_period, min_periods=bb_period).std(ddof=0)
        bb_upper = bb_mid + bb_std * bb_std_series
        bb_lower = bb_mid - bb_std * bb_std_series

        # --- Keltner Channel ---
        kc_mid = close.ewm(span=kc_period, adjust=False, min_periods=kc_period).mean()
        kc_atr = tr.ewm(alpha=1.0 / kc_period, adjust=False, min_periods=kc_period).mean()
        kc_upper = kc_mid + kc_mult * kc_atr
        kc_lower = kc_mid - kc_mult * kc_atr

        warmup = max(bb_period, kc_period, atr_slow) + 1

        if kind == "atr_ratio":
            atr_f = tr.ewm(alpha=1.0 / atr_fast, adjust=False, min_periods=atr_fast).mean()
            atr_s = tr.ewm(alpha=1.0 / atr_slow, adjust=False, min_periods=atr_slow).mean()
            values = atr_f / atr_s.replace(0.0, 1e-12)
            warmup = atr_slow + 1

        elif kind == "bb_squeeze":
            # 1 = squeeze فعال (bb داخل keltner)، 0 = بدون squeeze
            squeeze = (bb_upper <= kc_upper) & (bb_lower >= kc_lower)
            values = squeeze.astype(float)

        elif kind == "bb_width":
            values = (bb_upper - bb_lower) / close.replace(0.0, 1e-12)

        elif kind == "keltner_width":
            values = (kc_upper - kc_lower) / close.replace(0.0, 1e-12)

        elif kind == "squeeze_intensity":
            bb_w = (bb_upper - bb_lower) / close.replace(0.0, 1e-12)
            kc_w = (kc_upper - kc_lower) / close.replace(0.0, 1e-12)
            # منفی = squeeze قوی، مثبت = انبساط
            values = bb_w - kc_w

        else:
            raise ValueError(f"VolatilityBreakoutCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
