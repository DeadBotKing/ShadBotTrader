"""Candle Pattern features (causal).

این فیچرها الگوهای کندلی رو به عدد تبدیل می‌کنن
تا مدل ML بتونه ازشون یاد بگیره.

Features:
  - body_ratio      : نسبت body به کل کندل (High-Low)
  - upper_wick_ratio: نسبت سایه بالایی به کل کندل
  - lower_wick_ratio: نسبت سایه پایینی به کل کندل
  - engulfing       : الگوی پوشش‌دهنده (+1 صعودی، -1 نزولی، 0 هیچ‌کدام)
  - inside_bar      : آیا کندل داخل کندل قبلی هست؟ (0/1)
  - high_low_range  : مقیاس‌بندی محدوده High-Low نسبت به rolling ATR
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


class CandlePatternCalculator(FeatureCalculator):
    """محاسبه ساختار و الگوی کندل‌ها (همه causal).

    پارامترها:
      kind: نوع فیچر — یکی از:
        'body_ratio'      : |close-open| / (high-low)
        'upper_wick_ratio': (high - max(open,close)) / (high-low)
        'lower_wick_ratio': (min(open,close) - low) / (high-low)
        'engulfing'       : +1 صعودی، -1 نزولی، 0 خنثی
        'inside_bar'      : 1 اگه high < prev_high و low > prev_low
        'high_low_range'  : (high-low) / rolling_ATR — اندازه کندل نسبی
      period: دوره برای ATR در high_low_range (پیش‌فرض 14)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "body_ratio"))
        period = int(params.get("period", 14))

        frame = candle_frame(context)
        open_ = frame["open"]
        high = frame["high"]
        low = frame["low"]
        close = frame["close"]
        candle_range = (high - low).replace(0.0, 1e-12)

        if kind == "body_ratio":
            values = (close - open_).abs() / candle_range
            warmup = 0

        elif kind == "upper_wick_ratio":
            upper_body = pd.concat([open_, close], axis=1).max(axis=1)
            values = (high - upper_body) / candle_range
            warmup = 0

        elif kind == "lower_wick_ratio":
            lower_body = pd.concat([open_, close], axis=1).min(axis=1)
            values = (lower_body - low) / candle_range
            warmup = 0

        elif kind == "engulfing":
            prev_open = open_.shift(1)
            prev_close = close.shift(1)
            prev_body = (prev_close - prev_open)
            curr_body = (close - open_)

            # Bullish engulfing: کندل قبلی نزولی، کندل فعلی صعودی و بزرگ‌تر
            bull = (
                (prev_body < 0)
                & (curr_body > 0)
                & (open_ < prev_close)
                & (close > prev_open)
            )
            # Bearish engulfing: کندل قبلی صعودی، کندل فعلی نزولی و بزرگ‌تر
            bear = (
                (prev_body > 0)
                & (curr_body < 0)
                & (open_ > prev_close)
                & (close < prev_open)
            )
            values = bull.astype(float) - bear.astype(float)
            warmup = 1

        elif kind == "inside_bar":
            prev_high = high.shift(1)
            prev_low = low.shift(1)
            inside = (high < prev_high) & (low > prev_low)
            values = inside.astype(float)
            warmup = 1

        elif kind == "high_low_range":
            # True Range
            prev_close = close.shift(1)
            tr = pd.concat(
                [
                    high - low,
                    (high - prev_close).abs(),
                    (low - prev_close).abs(),
                ],
                axis=1,
            ).max(axis=1)
            atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            values = (high - low) / atr.replace(0.0, 1e-12)
            warmup = period

        else:
            raise ValueError(f"CandlePatternCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
