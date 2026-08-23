"""Market Regime features (causal).

این فیچرها «حالت بازار» رو تشخیص می‌دن:
  - آیا الان trending ایم یا ranging؟
  - volatility در چه سطحیه؟
  - آیا بازار در حال انبساط یا انقباض هست؟

Features:
  - hurst_exponent : اکسپوننت Hurst (≈0.5 رندوم، >0.5 روند، <0.5 mean-reverting)
  - efficiency_ratio: نسبت کارایی قیمت (چقدر مستقیم حرکت کرده)
  - vol_regime     : سطح volatility نسبی (z-score از ATR)
  - choppiness     : شاخص choppy بودن بازار (0=trend، 100=range)
"""

from __future__ import annotations

import math

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


class MarketRegimeCalculator(FeatureCalculator):
    """محاسبه حالت و رژیم بازار (همه causal).

    پارامترها:
      kind: نوع فیچر — یکی از:
        'efficiency_ratio': نسبت کارایی Kaufman (0 تا 1)
        'vol_regime'      : Z-Score از ATR در پنجره بلندمدت
        'choppiness'      : شاخص choppiness (14-100)
        'trend_score'     : امتیاز کلی روند (ترکیب چند اندیکاتور)
      period      : دوره کوتاه (پیش‌فرض 14)
      long_period : دوره بلند برای vol_regime (پیش‌فرض 50)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "efficiency_ratio"))
        period = int(params.get("period", 14))
        long_period = int(params.get("long_period", 50))

        frame = candle_frame(context)
        close = frame["close"]
        tr = _true_range(frame)

        if kind == "efficiency_ratio":
            # Kaufman Efficiency Ratio: چقدر مستقیم حرکت کرده؟
            # 1 = روند خالص، 0 = رندوم کامل
            net_change = close.diff(period).abs()
            path_length = close.diff().abs().rolling(period, min_periods=period).sum()
            values = net_change / path_length.replace(0.0, 1e-12)
            warmup = period

        elif kind == "vol_regime":
            # سطح volatility نسبی: ATR الان نسبت به ATR بلندمدت
            atr_short = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            atr_long = tr.ewm(alpha=1.0 / long_period, adjust=False, min_periods=long_period).mean()
            values = atr_short / atr_long.replace(0.0, 1e-12)
            warmup = long_period

        elif kind == "choppiness":
            # Choppiness Index: نزدیک 100 = ranging، نزدیک 0 = trending خالص
            atr_sum = tr.rolling(period, min_periods=period).sum()
            highest_high = frame["high"].rolling(period, min_periods=period).max()
            lowest_low = frame["low"].rolling(period, min_periods=period).min()
            total_range = (highest_high - lowest_low).replace(0.0, 1e-12)
            log_n = math.log10(period)
            values = 100.0 * (atr_sum / total_range).apply(
                lambda x: math.log10(x) if x > 0 else float("nan")
            ) / log_n
            warmup = period

        elif kind == "trend_score":
            # امتیاز ترکیبی روند: ترکیب EMA slope + efficiency ratio
            ema_fast = close.ewm(span=period, adjust=False, min_periods=period).mean()
            ema_slow = close.ewm(span=period * 3, adjust=False, min_periods=period * 3).mean()
            # جهت EMA: +1 صعودی، -1 نزولی
            ema_slope = (ema_fast - ema_slow) / ema_slow.replace(0.0, 1e-12)
            # Efficiency ratio
            net_change = close.diff(period)
            path_length = close.diff().abs().rolling(period, min_periods=period).sum()
            er = net_change.abs() / path_length.replace(0.0, 1e-12)
            # ترکیب: جهت × قوت
            values = ema_slope * er
            warmup = period * 3

        else:
            raise ValueError(f"MarketRegimeCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
