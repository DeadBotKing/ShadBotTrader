"""Market Structure Features — ساختار بازار (causal).

این فیچرها ساختار بازار رو از زوایای مختلف نگاه می‌کنن:

1. Pivot Points (کلاسیک و Fibonacci) — سطوح حمایت/مقاومت
2. Donchian Channel — کانال بالاترین-پایین‌ترین قیمت
3. Chandelier Exit — استاپ تریلینگ بر اساس ATR
4. Parabolic SAR (تقریبی ساده)
5. Linear Regression Features — شیب و R² روند خطی
6. Price Position Features — موقعیت قیمت نسبت به سطوح مختلف
7. Gap Features — شکاف قیمت بین کندل‌ها
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition
from ShadBotTrader.domain.feature.feature_result import FeatureResult
from ShadBotTrader.domain.feature.ports import FeatureCalculator, FeatureInputContext
from ShadBotTrader.infrastructure.feature.calculators.base import (
    candle_frame,
    result_from_series,
)


class StructureFeaturesCalculator(FeatureCalculator):
    """ساختار بازار و سطوح قیمتی (همه causal).

    kind:
      ── Donchian Channel ──
      'donchian_upper'  : بالاترین high در period کندل
      'donchian_lower'  : پایین‌ترین low در period کندل
      'donchian_mid'    : میانه کانال Donchian
      'donchian_pos'    : موقعیت نسبی قیمت در کانال (0 تا 1)
      'donchian_width'  : عرض نسبی کانال Donchian

      ── Linear Regression ──
      'linreg_slope'    : شیب خط رگرسیون خطی روی close (نرمال‌شده)
      'linreg_r2'       : R² رگرسیون — چقدر قیمت از خط خطی پیروی می‌کنه
      'linreg_deviation': انحراف قیمت از خط رگرسیون

      ── Gap Detection ──
      'gap_up'          : شکاف صعودی: open > prev_high (0/1)
      'gap_down'        : شکاف نزولی: open < prev_low (0/1)
      'gap_size'        : اندازه نسبی شکاف: (open - prev_close) / prev_close

      ── Price Position ──
      'close_vs_high'   : فاصله close از high روز: (high-close)/(high-low)
      'close_location'  : موقعیت close در کندل (0=پایین، 1=بالا)
      'overnight_gap'   : شکاف شب: (open - prev_close) / prev_close

      ── Chandelier Exit ──
      'chandelier_long' : استاپ long: highest_high - ATR_mult * ATR
      'chandelier_dist' : فاصله نسبی قیمت از Chandelier Exit

    period  : دوره (پیش‌فرض 20)
    atr_mult: ضریب ATR برای Chandelier (پیش‌فرض 3.0)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "donchian_pos"))
        period = int(params.get("period", 20))
        atr_mult = float(params.get("atr_mult", 3.0))

        frame = candle_frame(context)
        close = frame["close"]
        high = frame["high"]
        low = frame["low"]
        open_ = frame["open"]

        # ── Donchian Channel ───────────────────────────────────────────
        if kind in ("donchian_upper", "donchian_lower", "donchian_mid",
                    "donchian_pos", "donchian_width"):
            dc_high = high.rolling(period, min_periods=period).max()
            dc_low = low.rolling(period, min_periods=period).min()
            dc_mid = (dc_high + dc_low) / 2.0
            dc_range = (dc_high - dc_low).replace(0.0, 1e-12)

            if kind == "donchian_upper":
                values = dc_high
            elif kind == "donchian_lower":
                values = dc_low
            elif kind == "donchian_mid":
                values = dc_mid
            elif kind == "donchian_pos":
                values = (close - dc_low) / dc_range
            else:  # donchian_width
                values = dc_range / close.replace(0.0, 1e-12)
            warmup = period

        # ── Linear Regression ─────────────────────────────────────────
        elif kind in ("linreg_slope", "linreg_r2", "linreg_deviation"):
            prices = close.values.astype(float)
            n = len(prices)
            out = np.full(n, np.nan)

            for t in range(period - 1, n):
                y = prices[t - period + 1: t + 1]
                x = np.arange(period, dtype=float)
                xm, ym = x.mean(), y.mean()
                ssxx = np.sum((x - xm) ** 2)
                ssxy = np.sum((x - xm) * (y - ym))
                ssyy = np.sum((y - ym) ** 2)

                if ssxx < 1e-12:
                    continue

                slope = ssxy / ssxx
                intercept = ym - slope * xm
                y_pred_last = slope * (period - 1) + intercept

                if kind == "linreg_slope":
                    # شیب نرمال‌شده به قیمت
                    out[t] = slope / (ym + 1e-12)
                elif kind == "linreg_r2":
                    r2 = (ssxy ** 2) / (ssxx * ssyy) if ssyy > 1e-12 else 0.0
                    out[t] = max(0.0, min(1.0, r2))
                else:  # linreg_deviation
                    out[t] = (prices[t] - y_pred_last) / (ym + 1e-12)

            values = pd.Series(out, index=frame.index)
            warmup = period

        # ── Gap Detection ─────────────────────────────────────────────
        elif kind in ("gap_up", "gap_down", "gap_size", "overnight_gap"):
            prev_high = high.shift(1)
            prev_low = low.shift(1)
            prev_close = close.shift(1).replace(0.0, 1e-12)

            if kind == "gap_up":
                values = (open_ > prev_high).astype(float)
            elif kind == "gap_down":
                values = (open_ < prev_low).astype(float)
            elif kind == "gap_size":
                values = (open_ - prev_close) / prev_close
            else:  # overnight_gap
                values = (open_ - prev_close) / prev_close
            warmup = 1

        # ── Price Position ────────────────────────────────────────────
        elif kind in ("close_vs_high", "close_location"):
            hl_range = (high - low).replace(0.0, 1e-12)
            if kind == "close_vs_high":
                values = (high - close) / hl_range
            else:  # close_location: (close-low)/(high-low)
                values = (close - low) / hl_range
            warmup = 0

        # ── Chandelier Exit ───────────────────────────────────────────
        elif kind in ("chandelier_long", "chandelier_dist"):
            prev_close = close.shift(1)
            tr = pd.concat([
                high - low,
                (high - prev_close).abs(),
                (low - prev_close).abs(),
            ], axis=1).max(axis=1)
            atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            highest_high = high.rolling(period, min_periods=period).max()
            chandelier = highest_high - atr_mult * atr

            if kind == "chandelier_long":
                values = chandelier
            else:  # chandelier_dist
                values = (close - chandelier) / close.replace(0.0, 1e-12)
            warmup = period

        else:
            raise ValueError(f"StructureFeaturesCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
