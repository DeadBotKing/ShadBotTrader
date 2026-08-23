"""Ehlers Advanced Indicators — کتاب‌های Cycle Analytics و Cybernetic Analysis.

منابع:
  - Ehlers, "Cycle Analytics for Traders" (2013): ReFlex, TrendFlex, Even Better Sinewave
  - Ehlers, "Cybernetic Analysis" (2004): Relative Vigor Index, Decycler
  - Ehlers, "Rocket Science for Traders" (2001): Instantaneous Trendline

همه این فیچرها causal (فقط از داده گذشته) هستن.

1. ReFlex    — اوسیلاتور "رفلکس": انحراف قیمت از خط روند پیش‌بینی‌شده
2. TrendFlex — اوسیلاتور "ترندفلکس": قوت روند نرمال‌شده
3. Even Better Sinewave (EBSW) — موج سینوسی بهتر: بازار cyclic یا trending؟
4. Relative Vigor Index (RVI) — قدرت نسبی بر اساس close vs open
5. Decycler  — حذف سیکل، نمایش ترند خالص
6. Decycler Oscillator — اوسیلاتور decycler
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


def _supersmoother_vec(prices: np.ndarray, period: int) -> np.ndarray:
    """Ehlers SuperSmoother 2-pole (causal)."""
    n = len(prices)
    out = np.full(n, np.nan)
    sq2 = math.sqrt(2.0)
    a1 = math.exp(-sq2 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(math.radians(sq2 * 180.0 / period))
    c2, c3 = b1, -(a1 ** 2)
    c1 = 1.0 - c2 - c3
    for t in range(2, n):
        p1 = out[t - 1] if not np.isnan(out[t - 1]) else prices[t - 1]
        p2 = out[t - 2] if not np.isnan(out[t - 2]) else prices[t - 2]
        out[t] = c1 * (prices[t] + prices[t - 1]) / 2.0 + c2 * p1 + c3 * p2
    return out


class EhlersAdvancedCalculator(FeatureCalculator):
    """اندیکاتورهای پیشرفته Ehlers از کتاب‌های Cycle Analytics و Cybernetic.

    kind:
      'reflex'         : ReFlex oscillator — انحراف از خط روند (Cycle Analytics 2013)
      'trendflex'      : TrendFlex oscillator — قوت روند (Cycle Analytics 2013)
      'ebsw'           : Even Better Sinewave — بازار cyclic یا trending
      'rvi'            : Relative Vigor Index — close vs open نرمال‌شده
      'rvi_signal'     : RVI Signal line (4-tap WMA)
      'decycler'       : Decycler — ترند خالص بدون سیکل
      'decycler_osc'   : Decycler Oscillator — تفاضل دو decycler
    period     : دوره اصلی (پیش‌فرض 20)
    hp_period  : دوره High-Pass برای EBSW و Decycler (پیش‌فرض 40)
    fast_hp    : دوره سریع برای Decycler Oscillator (پیش‌فرض 10)
    slow_hp    : دوره کند برای Decycler Oscillator (پیش‌فرض 20)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        p = definition.parameters
        kind = str(p.get("kind", "reflex"))
        period = int(p.get("period", 20))
        hp_period = int(p.get("hp_period", 40))
        fast_hp = int(p.get("fast_hp", 10))
        slow_hp = int(p.get("slow_hp", 20))

        frame = candle_frame(context)
        close = frame["close"].values.astype(float)
        open_ = frame["open"].values.astype(float)
        high = frame["high"].values.astype(float)
        low = frame["low"].values.astype(float)
        n = len(close)

        # ── SuperSmoother مشترک ──────────────────────────────────────────
        filt = _supersmoother_vec(close, period)

        if kind == "reflex":
            # ReFlex: انحراف قیمت فیلترشده از یه خط روند پیش‌بینی‌شده
            # Slope = (Filt[t-period] - Filt[t]) / period
            # Sum = avg(Filt[t] + i*Slope - Filt[t-i]) for i=1..period
            out = np.full(n, np.nan)
            ms = 0.0
            for t in range(period + 2, n):
                if np.isnan(filt[t]) or np.isnan(filt[t - period]):
                    continue
                slope = (filt[t - period] - filt[t]) / period
                s = sum(
                    (filt[t] + i * slope) - filt[t - i]
                    for i in range(1, period + 1)
                    if not np.isnan(filt[t - i])
                ) / period
                ms = 0.04 * s * s + 0.96 * ms
                out[t] = s / math.sqrt(ms) if ms > 1e-12 else 0.0
            values = pd.Series(out, index=frame.index)
            warmup = period + 3

        elif kind == "trendflex":
            # TrendFlex: تفاوت قیمت فیلترشده فعلی از تاریخ
            out = np.full(n, np.nan)
            ms = 0.0
            for t in range(period + 2, n):
                if np.isnan(filt[t]):
                    continue
                s = sum(
                    filt[t] - filt[t - i]
                    for i in range(1, period + 1)
                    if not np.isnan(filt[t - i])
                ) / period
                ms = 0.04 * s * s + 0.96 * ms
                out[t] = s / math.sqrt(ms) if ms > 1e-12 else 0.0
            values = pd.Series(out, index=frame.index)
            warmup = period + 3

        elif kind == "ebsw":
            # Even Better Sinewave (Ehlers, Cycle Analytics 2013)
            # HP 1-pole → SuperSmoother → Wave / sqrt(Power)
            hp_period_eb = int(p.get("hp_period", 36))
            ss_period_eb = int(p.get("period", 10))
            angle = 2.0 * math.pi / hp_period_eb
            alpha1 = (1.0 - math.sin(angle)) / math.cos(angle)
            hp = np.zeros(n)
            for t in range(1, n):
                hp[t] = 0.5 * (1.0 + alpha1) * (close[t] - close[t - 1]) + alpha1 * hp[t - 1]
            filt_eb = _supersmoother_vec(hp, ss_period_eb)
            out = np.full(n, np.nan)
            for t in range(2, n):
                if any(np.isnan(filt_eb[t - i]) for i in range(3)):
                    continue
                wave = (filt_eb[t] + filt_eb[t - 1] + filt_eb[t - 2]) / 3.0
                pwr = (filt_eb[t] ** 2 + filt_eb[t - 1] ** 2 + filt_eb[t - 2] ** 2) / 3.0
                out[t] = wave / math.sqrt(pwr) if pwr > 1e-12 else 0.0
            values = pd.Series(out, index=frame.index)
            warmup = hp_period_eb + ss_period_eb

        elif kind in ("rvi", "rvi_signal"):
            # Relative Vigor Index (Ehlers, Cybernetic Analysis 2004)
            # Numerator = (close-open) با wma4  Denominator = (high-low) با wma4
            numerator = (close - open_)
            denominator = (high - low)

            def wma4(arr: np.ndarray) -> np.ndarray:
                out = np.full(n, np.nan)
                for t in range(3, n):
                    out[t] = (arr[t] + 2 * arr[t - 1] + 2 * arr[t - 2] + arr[t - 3]) / 6.0
                return out

            num_s = wma4(numerator)
            den_s = wma4(denominator)
            rvi_arr = np.full(n, np.nan)
            for t in range(6, n):
                num_sum = sum(
                    num_s[t - i] for i in range(4) if not np.isnan(num_s[t - i])
                )
                den_sum = sum(
                    den_s[t - i] for i in range(4) if not np.isnan(den_s[t - i])
                )
                rvi_arr[t] = num_sum / den_sum if abs(den_sum) > 1e-12 else 0.0

            if kind == "rvi":
                values = pd.Series(rvi_arr, index=frame.index)
            else:  # rvi_signal: 4-tap WMA روی RVI
                sig = wma4(np.where(np.isnan(rvi_arr), 0.0, rvi_arr))
                values = pd.Series(sig, index=frame.index)
            warmup = 10

        elif kind in ("decycler", "decycler_osc"):
            # Decycler (Ehlers, Cycle Analytics 2013)
            # High-Pass 1-pole حذف سیکل، Decycler = price - HP
            def _hp1(arr, per):
                ang = 2.0 * math.pi / per
                a1 = (1.0 - math.sin(ang)) / math.cos(ang)
                hp = np.zeros(n)
                for t in range(1, n):
                    hp[t] = 0.5 * (1.0 + a1) * (arr[t] - arr[t - 1]) + a1 * hp[t - 1]
                return hp

            if kind == "decycler":
                hp = _hp1(close, hp_period)
                dec = close - hp
                values = pd.Series(dec, index=frame.index)
                warmup = hp_period
            else:  # decycler_osc: تفاضل دو decycler
                hp_fast = _hp1(close, fast_hp)
                hp_slow = _hp1(close, slow_hp)
                dec_fast = close - hp_fast
                dec_slow = close - hp_slow
                osc = 100.0 * (dec_fast - dec_slow) / np.where(dec_slow != 0, dec_slow, 1e-12)
                values = pd.Series(osc, index=frame.index)
                warmup = slow_hp

        else:
            raise ValueError(f"EhlersAdvancedCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
