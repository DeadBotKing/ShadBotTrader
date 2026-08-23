"""Mean Reversion features (causal).

استراتژی Mean Reversion:
  قیمت وقتی از میانگین دور می‌شه، تمایل به بازگشت داره.
  این فیچرها نشون می‌دن قیمت چقدر از «تعادل» فاصله گرفته.

Features:
  - zscore        : Z-Score قیمت نسبت به میانگین نورمال‌شده
  - rsi_distance  : فاصله RSI از ناحیه خنثی (50)
  - bb_position   : موقعیت قیمت داخل باند Bollinger (-1 تا +2)
  - close_vs_vwap : فاصله نسبی قیمت از VWAP (میانگین وزنی حجمی)
  - momentum_5_20 : مومنتوم کوتاه‌مدت vs بلندمدت (mean reversion signal)
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


class MeanReversionCalculator(FeatureCalculator):
    """محاسبه فیچرهای Mean Reversion (همه causal).

    پارامترها:
      kind: نوع فیچر — یکی از:
        'zscore'        : Z-Score قیمت (close) در پنجره rolling
        'rsi_distance'  : RSI - 50 (مثبت = اشباع خرید، منفی = اشباع فروش)
        'bb_position'   : موقعیت Bollinger %B
        'close_vs_vwap' : (close - VWAP) / VWAP
        'momentum_ratio': return(fast) / return(slow) — نسبت مومنتوم
      period : دوره rolling (پیش‌فرض 20)
      fast   : دوره کوتاه برای momentum_ratio (پیش‌فرض 5)
      slow   : دوره بلند برای momentum_ratio (پیش‌فرض 20)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "zscore"))
        period = int(params.get("period", 20))
        fast = int(params.get("fast", 5))
        slow = int(params.get("slow", 20))

        frame = candle_frame(context)
        close = frame["close"]

        if kind == "zscore":
            roll_mean = close.rolling(period, min_periods=period).mean()
            roll_std = close.rolling(period, min_periods=period).std(ddof=0).replace(0.0, 1e-12)
            values = (close - roll_mean) / roll_std
            warmup = period

        elif kind == "rsi_distance":
            # RSI با Wilder smoothing، سپس فاصله از 50
            delta = close.diff()
            gain = delta.clip(lower=0.0)
            loss = -delta.clip(upper=0.0)
            avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            rs = avg_gain / avg_loss.replace(0.0, 1e-12)
            rsi = 100.0 - (100.0 / (1.0 + rs))
            values = rsi - 50.0  # مثبت = overbought، منفی = oversold
            warmup = period

        elif kind == "bb_position":
            # Bollinger %B: 0 = خط پایین، 1 = خط بالا، >1 یا <0 = خارج از باند
            bb_mid = close.rolling(period, min_periods=period).mean()
            bb_std_s = close.rolling(period, min_periods=period).std(ddof=0)
            bb_upper = bb_mid + 2.0 * bb_std_s
            bb_lower = bb_mid - 2.0 * bb_std_s
            denom = (bb_upper - bb_lower).replace(0.0, 1e-12)
            values = (close - bb_lower) / denom
            warmup = period

        elif kind == "close_vs_vwap":
            # VWAP rolling (استفاده از حجم واقعی)
            volume = frame["volume"].replace(0.0, 1e-12)
            typical = (frame["high"] + frame["low"] + close) / 3.0
            cumulative_tp_vol = (typical * volume).rolling(period, min_periods=period).sum()
            cumulative_vol = volume.rolling(period, min_periods=period).sum().replace(0.0, 1e-12)
            vwap = cumulative_tp_vol / cumulative_vol
            values = (close - vwap) / vwap.replace(0.0, 1e-12)
            warmup = period

        elif kind == "momentum_ratio":
            # نسبت return کوتاه‌مدت به بلندمدت
            # اگه > 1: momentum ادامه‌دار، اگه < 1: احتمال reversal
            ret_fast = close.pct_change(fast)
            ret_slow = close.pct_change(slow)
            values = ret_fast / ret_slow.replace(0.0, 1e-12).abs()
            warmup = slow

        else:
            raise ValueError(f"MeanReversionCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
