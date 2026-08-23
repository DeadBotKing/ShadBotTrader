"""Session & Time features (causal).

ویژگی‌های زمانی و session بازار:
طلا (XAUUSD) در سه session اصلی معامله می‌شه و هر کدوم رفتار متفاوتی دارن:

- Asian session  (00:00 - 08:00 UTC): آروم‌تر، ranging
- London session (08:00 - 16:00 UTC): پرنوسان‌ترین بخش
- NY session     (13:00 - 21:00 UTC): حجم بالا، overlap با London

Features:
  - session_asian   : آیا الان session آسیا است؟ (0/1)
  - session_london  : آیا الان session لندن است؟ (0/1)
  - session_ny      : آیا الان session نیویورک است؟ (0/1)
  - session_overlap : آیا overlap لندن-NY است؟ (0/1)
  - hour_sin/cos    : ساعت روز به صورت چرخه‌ای (برای ML)
  - day_sin/cos     : روز هفته به صورت چرخه‌ای
  - minutes_to_close: دقیقه تا پایان روز معاملاتی (نسبی)

Reference:
  - DRL trading: https://github.com/zero-was-here/tradingbot (session features)
  - mql5 Golden Gauss: https://www.mql5.com/en/blogs/post/767489 (active hours)
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


class SessionTimeCalculator(FeatureCalculator):
    """فیچرهای زمانی و session بازار (همه causal، بدون look-ahead).

    پارامترها:
      kind: نوع فیچر — یکی از:
        'session_asian'   : 1 اگه Asian session (00-08 UTC)
        'session_london'  : 1 اگه London session (08-16 UTC)
        'session_ny'      : 1 اگه NY session (13-21 UTC)
        'session_overlap' : 1 اگه London-NY overlap (13-16 UTC)
        'hour_sin'        : sin ساعت UTC (تناوب ۲۴ ساعته)
        'hour_cos'        : cos ساعت UTC
        'day_sin'         : sin روز هفته (0=دوشنبه، 4=جمعه)
        'day_cos'         : cos روز هفته
        'is_monday'       : آیا دوشنبه است؟ (شروع هفته)
        'is_friday'       : آیا جمعه است؟ (پایان هفته)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "hour_sin"))

        frame = candle_frame(context)
        # open_time به UTC تبدیل می‌کنیم
        timestamps = pd.to_datetime(frame["open_time"], unit="s", utc=True)

        hour = timestamps.dt.hour
        minute = timestamps.dt.minute
        dow = timestamps.dt.dayofweek  # 0=Monday, 4=Friday

        if kind == "session_asian":
            values = ((hour >= 0) & (hour < 8)).astype(float)

        elif kind == "session_london":
            values = ((hour >= 8) & (hour < 16)).astype(float)

        elif kind == "session_ny":
            values = ((hour >= 13) & (hour < 21)).astype(float)

        elif kind == "session_overlap":
            # London-NY overlap: ۱۳:۰۰ - ۱۶:۰۰ UTC پرنوسان‌ترین بخش روز
            values = ((hour >= 13) & (hour < 16)).astype(float)

        elif kind == "hour_sin":
            # ساعت رو به فرم چرخه‌ای درمیاریم — برای مدل ML بهتره از raw hour
            hour_float = hour + minute / 60.0
            values = hour_float.apply(lambda h: math.sin(2 * math.pi * h / 24.0))

        elif kind == "hour_cos":
            hour_float = hour + minute / 60.0
            values = hour_float.apply(lambda h: math.cos(2 * math.pi * h / 24.0))

        elif kind == "day_sin":
            values = dow.apply(lambda d: math.sin(2 * math.pi * d / 5.0))

        elif kind == "day_cos":
            values = dow.apply(lambda d: math.cos(2 * math.pi * d / 5.0))

        elif kind == "is_monday":
            values = (dow == 0).astype(float)

        elif kind == "is_friday":
            values = (dow == 4).astype(float)

        else:
            raise ValueError(f"SessionTimeCalculator: kind نامعتبر: {kind!r}")

        # همه این فیچرها بدون warmup هستن (instantaneous)
        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=pd.Series(values.values, index=frame.index),
            warmup=0,
        )
