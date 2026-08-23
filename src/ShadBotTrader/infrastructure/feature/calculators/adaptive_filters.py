"""Adaptive Filters — فیلترهای تطبیقی پیشرفته (همه causal).

منابع اصلی:
  - John Ehlers: "Rocket Science for Traders" (2001)
  - John Ehlers: "Cybernetic Analysis for Stocks and Futures" (2004)
  - John Ehlers: "Cycle Analytics for Traders" (2013)
  - Kaufman: "Trading Systems and Methods" (KAMA)
  - Chande: "Beyond Technical Analysis" (VIDYA)

فیلترهایی که پیاده‌سازی شدن:

1. KAMA   — Kaufman Adaptive Moving Average
   سرعت خودش رو بر اساس Efficiency Ratio تنظیم می‌کنه
   در روند سریع و در رنج کند می‌شه

2. SuperSmoother (Ehlers 2-pole IIR)
   از کتاب "Cybernetic Analysis" — بهترین جایگزین MA با نویز خیلی کمتر
   فرکانس‌های بالا (نویز) رو حذف می‌کنه

3. Gaussian Filter (1, 2, 3 pole)
   فیلتر Gaussian با تعداد pole متغیر — صاف‌تر = بیشتر pole

4. FRAMA — Fractal Adaptive Moving Average (Ehlers)
   از بُعد فراکتال قیمت برای تنظیم سرعت استفاده می‌کنه
   در رنج کند، در روند سریع

5. Hull MA
   sqrt(period) lag — سریع‌ترین MA با نویز کم

6. McGinley Dynamic
   خودش alpha رو dynamic تنظیم می‌کنه — کمتر whipsaw

7. VIDYA — Variable Index Dynamic Average (Chande)
   از CMO (Chande Momentum) برای تنظیم alpha استفاده می‌کنه

8. Laguerre Filter (Ehlers)
   4-tap Laguerre با پارامتر gamma — lag کمتر از EMA
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


# ─────────────────────────────────────────────────────────────────────────────
# KAMA — Kaufman Adaptive Moving Average
# ─────────────────────────────────────────────────────────────────────────────
def _kama(prices: np.ndarray, period: int = 10, fast: int = 2, slow: int = 30) -> np.ndarray:
    """KAMA — Kaufman Adaptive Moving Average (causal recursive).

    SC = (ER × (fast_sc - slow_sc) + slow_sc)²
    KAMA[t] = KAMA[t-1] + SC × (price[t] - KAMA[t-1])
    """
    n = len(prices)
    result = np.full(n, np.nan)
    fast_sc = 2.0 / (fast + 1.0)
    slow_sc = 2.0 / (slow + 1.0)

    for i in range(period, n):
        # Efficiency Ratio
        direction = abs(prices[i] - prices[i - period])
        volatility = sum(abs(prices[j] - prices[j - 1]) for j in range(i - period + 1, i + 1))
        er = direction / volatility if volatility > 1e-12 else 0.0
        sc = (er * (fast_sc - slow_sc) + slow_sc) ** 2

        if np.isnan(result[i - 1]):
            result[i] = prices[i]
        else:
            result[i] = result[i - 1] + sc * (prices[i] - result[i - 1])

    return result


# ─────────────────────────────────────────────────────────────────────────────
# SuperSmoother (Ehlers 2-pole IIR)
# ─────────────────────────────────────────────────────────────────────────────
def _supersmoother(prices: np.ndarray, period: int = 10) -> np.ndarray:
    """Ehlers SuperSmoother — 2-pole IIR causal filter.

    از کتاب "Cybernetic Analysis for Stocks and Futures" (2004)
    فرمول:
      a1 = exp(-√2 × π / period)
      b1 = 2 × a1 × cos(√2 × π / period)
      c2 = b1;  c3 = -a1²;  c1 = 1 - c2 - c3
      SS[t] = c1 × (price[t] + price[t-1]) / 2 + c2 × SS[t-1] + c3 × SS[t-2]
    """
    n = len(prices)
    result = np.full(n, np.nan)
    sq2 = math.sqrt(2.0)
    a1 = math.exp(-sq2 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(math.radians(sq2 * 180.0 / period))
    c2 = b1
    c3 = -(a1 ** 2)
    c1 = 1.0 - c2 - c3

    for t in range(2, n):
        mid = (prices[t] + prices[t - 1]) / 2.0
        prev1 = result[t - 1] if not np.isnan(result[t - 1]) else prices[t - 1]
        prev2 = result[t - 2] if not np.isnan(result[t - 2]) else prices[t - 2]
        result[t] = c1 * mid + c2 * prev1 + c3 * prev2

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Gaussian Filter (Ehlers)
# ─────────────────────────────────────────────────────────────────────────────
def _gaussian_filter(prices: np.ndarray, period: int = 10, poles: int = 2) -> np.ndarray:
    """Ehlers Gaussian Filter — 1, 2, یا 3 pole causal.

    از مقاله Ehlers "Gaussian and Other Low Lag Filters"
    هرچه poles بیشتر = صاف‌تر و lag کمی بیشتر
    """
    n = len(prices)
    result = np.full(n, np.nan)
    beta = 2.0 - math.cos(2.0 * math.pi / period)
    alpha = beta - math.sqrt(beta ** 2 - 1.0)

    if poles == 1:
        for t in range(1, n):
            prev = result[t - 1] if not np.isnan(result[t - 1]) else prices[t - 1]
            result[t] = alpha * prices[t] + (1.0 - alpha) * prev

    elif poles == 2:
        prev2 = np.full(n, np.nan)
        for t in range(1, n):
            p1 = result[t - 1] if not np.isnan(result[t - 1]) else prices[t - 1]
            p2 = prev2[t - 1] if not np.isnan(prev2[t - 1]) else prices[t - 1]
            prev2[t] = alpha * prices[t] + (1.0 - alpha) * p1
            result[t] = alpha * prev2[t] + (1.0 - alpha) * p2

    elif poles == 3:
        s1 = np.full(n, np.nan)
        s2 = np.full(n, np.nan)
        for t in range(1, n):
            q1 = s1[t - 1] if not np.isnan(s1[t - 1]) else prices[t - 1]
            q2 = s2[t - 1] if not np.isnan(s2[t - 1]) else prices[t - 1]
            q3 = result[t - 1] if not np.isnan(result[t - 1]) else prices[t - 1]
            s1[t] = alpha * prices[t] + (1.0 - alpha) * q1
            s2[t] = alpha * s1[t] + (1.0 - alpha) * q2
            result[t] = alpha * s2[t] + (1.0 - alpha) * q3

    return result


# ─────────────────────────────────────────────────────────────────────────────
# FRAMA — Fractal Adaptive Moving Average (Ehlers)
# ─────────────────────────────────────────────────────────────────────────────
def _frama(high: np.ndarray, low: np.ndarray, period: int = 16) -> np.ndarray:
    """FRAMA — Fractal Adaptive Moving Average (Ehlers, causal).

    بُعد فراکتال D از رابطه scaling محاسبه می‌شه:
      N1 = (High1 - Low1) / half_period
      N2 = (High2 - Low2) / half_period
      N3 = (High_full - Low_full) / period
      D  = (log(N1+N2) - log(N3)) / log(2)
      alpha = exp(-4.6 × (D - 1))
    """
    n = len(high)
    result = np.full(n, np.nan)
    half = period // 2

    for t in range(period - 1, n):
        # نیمه اول
        h1 = np.max(high[t - period + 1: t - half + 1])
        l1 = np.min(low[t - period + 1: t - half + 1])
        # نیمه دوم
        h2 = np.max(high[t - half + 1: t + 1])
        l2 = np.min(low[t - half + 1: t + 1])
        # کل
        h3 = np.max(high[t - period + 1: t + 1])
        l3 = np.min(low[t - period + 1: t + 1])

        n1 = (h1 - l1) / half if half > 0 else 1e-12
        n2 = (h2 - l2) / half if half > 0 else 1e-12
        n3 = (h3 - l3) / period if period > 0 else 1e-12

        if (n1 + n2) > 0 and n3 > 0:
            dim = (math.log(n1 + n2) - math.log(n3)) / math.log(2.0)
            dim = max(1.0, min(2.0, dim))
            alpha = math.exp(-4.6 * (dim - 1.0))
            alpha = max(0.01, min(1.0, alpha))
        else:
            alpha = 0.01

        mid_price = (high[t] + low[t]) / 2.0
        if np.isnan(result[t - 1]):
            result[t] = mid_price
        else:
            result[t] = alpha * mid_price + (1.0 - alpha) * result[t - 1]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Hull Moving Average
# ─────────────────────────────────────────────────────────────────────────────
def _hull_ma(prices: pd.Series, period: int = 14) -> pd.Series:
    """Hull Moving Average: WMA(2×WMA(n/2) - WMA(n), sqrt(n)).

    تقریباً بدون lag با نویز کم.
    """
    half = max(2, period // 2)
    sqrt_p = max(2, int(round(math.sqrt(period))))

    def wma(s: pd.Series, p: int) -> pd.Series:
        weights = np.arange(1, p + 1, dtype=float)
        return s.rolling(p, min_periods=p).apply(
            lambda x: np.dot(x, weights) / weights.sum(), raw=True
        )

    wma_half = wma(prices, half)
    wma_full = wma(prices, period)
    raw = 2.0 * wma_half - wma_full
    return wma(raw, sqrt_p)


# ─────────────────────────────────────────────────────────────────────────────
# McGinley Dynamic
# ─────────────────────────────────────────────────────────────────────────────
def _mcginley_dynamic(prices: np.ndarray, period: int = 14) -> np.ndarray:
    """McGinley Dynamic Average (causal).

    MD[t] = MD[t-1] + (price[t] - MD[t-1]) / (N × (price/MD[t-1])^4)
    خودکار سریع می‌شه وقتی قیمت دور می‌شه.
    """
    n = len(prices)
    result = np.full(n, np.nan)
    result[0] = prices[0]

    for t in range(1, n):
        prev = result[t - 1] if not np.isnan(result[t - 1]) else prices[t - 1]
        if prev > 1e-12:
            ratio = prices[t] / prev
            denom = period * (ratio ** 4)
            result[t] = prev + (prices[t] - prev) / max(denom, 1e-12)
        else:
            result[t] = prices[t]

    return result


# ─────────────────────────────────────────────────────────────────────────────
# VIDYA — Variable Index Dynamic Average (Chande)
# ─────────────────────────────────────────────────────────────────────────────
def _vidya(prices: np.ndarray, period: int = 14, fast_period: int = 9) -> np.ndarray:
    """VIDYA — Variable Index Dynamic Average (Chande, causal).

    alpha = fast_alpha × |CMO| / 100
    CMO = (up - down) / (up + down) × 100  در پنجره period
    """
    n = len(prices)
    result = np.full(n, np.nan)
    fast_alpha = 2.0 / (fast_period + 1.0)

    for t in range(period, n):
        segment = prices[t - period: t + 1]
        diff = np.diff(segment)
        up = float(np.sum(diff[diff > 0]))
        down = float(np.sum(np.abs(diff[diff < 0])))
        total = up + down
        cmo_abs = abs((up - down) / total) if total > 1e-12 else 0.0
        alpha = fast_alpha * cmo_abs

        prev = result[t - 1] if not np.isnan(result[t - 1]) else prices[t - 1]
        result[t] = alpha * prices[t] + (1.0 - alpha) * prev

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Laguerre Filter (Ehlers)
# ─────────────────────────────────────────────────────────────────────────────
def _laguerre_filter(prices: np.ndarray, gamma: float = 0.8) -> np.ndarray:
    """Ehlers 4-tap Laguerre Filter (causal).

    از کتاب "Cybernetic Analysis" — lag خیلی کم، نویز کم
    L0[t] = (1-γ)×price[t] + γ×L0[t-1]
    L1[t] = -γ×L0[t] + L0[t-1] + γ×L1[t-1]
    L2[t] = -γ×L1[t] + L1[t-1] + γ×L2[t-1]
    L3[t] = -γ×L2[t] + L2[t-1] + γ×L3[t-1]
    Filt  = (L0 + 2L1 + 2L2 + L3) / 6
    """
    n = len(prices)
    result = np.full(n, np.nan)
    L0_prev = L1_prev = L2_prev = L3_prev = prices[0]

    for t in range(n):
        L0 = (1.0 - gamma) * prices[t] + gamma * L0_prev
        L1 = -gamma * L0 + L0_prev + gamma * L1_prev
        L2 = -gamma * L1 + L1_prev + gamma * L2_prev
        L3 = -gamma * L2 + L2_prev + gamma * L3_prev
        result[t] = (L0 + 2.0 * L1 + 2.0 * L2 + L3) / 6.0
        L0_prev, L1_prev, L2_prev, L3_prev = L0, L1, L2, L3

    return result


# ─────────────────────────────────────────────────────────────────────────────
# Calculator class
# ─────────────────────────────────────────────────────────────────────────────
class AdaptiveFiltersCalculator(FeatureCalculator):
    """فیلترهای تطبیقی پیشرفته (همه causal — بدون look-ahead).

    پارامترها:
      kind: نوع فیچر — یکی از:
        ── فیلترهای تطبیقی ──
        'kama'            : Kaufman Adaptive MA
        'kama_distance'   : فاصله نسبی قیمت از KAMA
        'supersmoother'   : Ehlers 2-pole SuperSmoother
        'ss_distance'     : فاصله نسبی قیمت از SuperSmoother
        'gaussian1'       : Gaussian Filter 1-pole
        'gaussian2'       : Gaussian Filter 2-pole
        'gaussian3'       : Gaussian Filter 3-pole
        'frama'           : Fractal Adaptive MA (Ehlers)
        'frama_distance'  : فاصله نسبی قیمت از FRAMA
        'hull_ma'         : Hull Moving Average
        'hull_distance'   : فاصله نسبی قیمت از Hull MA
        'mcginley'        : McGinley Dynamic Average
        'mcginley_distance': فاصله نسبی قیمت از McGinley
        'vidya'           : Variable Index Dynamic Average (Chande)
        'vidya_distance'  : فاصله نسبی قیمت از VIDYA
        'laguerre'        : Ehlers Laguerre Filter
        'laguerre_distance': فاصله نسبی قیمت از Laguerre

      period : دوره اصلی (پیش‌فرض 14)
      fast   : دوره fast برای KAMA (پیش‌فرض 2)
      slow   : دوره slow برای KAMA (پیش‌فرض 30)
      poles  : تعداد pole برای Gaussian (1, 2, یا 3)
      gamma  : پارامتر Laguerre (0-1، پیش‌فرض 0.8)
      column : ستون قیمت (پیش‌فرض 'close')
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "kama"))
        period = int(params.get("period", 14))
        fast = int(params.get("fast", 2))
        slow = int(params.get("slow", 30))
        poles = int(params.get("poles", 2))
        gamma = float(params.get("gamma", 0.8))
        column = str(params.get("column", "close"))

        frame = candle_frame(context)
        close = frame[column]
        prices = close.values.astype(float)

        if kind in ("kama", "kama_distance"):
            filtered = _kama(prices, period=period, fast=fast, slow=slow)
            warmup = period
            if kind == "kama":
                values = pd.Series(filtered, index=frame.index)
            else:
                ks = pd.Series(filtered, index=frame.index)
                values = (close - ks) / ks.replace(0.0, 1e-12)

        elif kind in ("supersmoother", "ss_distance"):
            filtered = _supersmoother(prices, period=period)
            warmup = period
            if kind == "supersmoother":
                values = pd.Series(filtered, index=frame.index)
            else:
                ss = pd.Series(filtered, index=frame.index)
                values = (close - ss) / ss.replace(0.0, 1e-12)

        elif kind in ("gaussian1", "gaussian2", "gaussian3"):
            p = {"gaussian1": 1, "gaussian2": 2, "gaussian3": 3}[kind]
            filtered = _gaussian_filter(prices, period=period, poles=p)
            warmup = period
            values = pd.Series(filtered, index=frame.index)

        elif kind in ("frama", "frama_distance"):
            high = frame["high"].values.astype(float)
            low = frame["low"].values.astype(float)
            filtered = _frama(high, low, period=period)
            warmup = period
            if kind == "frama":
                values = pd.Series(filtered, index=frame.index)
            else:
                fs = pd.Series(filtered, index=frame.index)
                values = (close - fs) / fs.replace(0.0, 1e-12)

        elif kind in ("hull_ma", "hull_distance"):
            filtered = _hull_ma(close, period=period)
            warmup = period
            if kind == "hull_ma":
                values = filtered
            else:
                values = (close - filtered) / filtered.replace(0.0, 1e-12)

        elif kind in ("mcginley", "mcginley_distance"):
            filtered = _mcginley_dynamic(prices, period=period)
            warmup = 1
            if kind == "mcginley":
                values = pd.Series(filtered, index=frame.index)
            else:
                ms = pd.Series(filtered, index=frame.index)
                values = (close - ms) / ms.replace(0.0, 1e-12)

        elif kind in ("vidya", "vidya_distance"):
            filtered = _vidya(prices, period=period)
            warmup = period
            if kind == "vidya":
                values = pd.Series(filtered, index=frame.index)
            else:
                vs = pd.Series(filtered, index=frame.index)
                values = (close - vs) / vs.replace(0.0, 1e-12)

        elif kind in ("laguerre", "laguerre_distance"):
            filtered = _laguerre_filter(prices, gamma=gamma)
            warmup = 4
            if kind == "laguerre":
                values = pd.Series(filtered, index=frame.index)
            else:
                ls = pd.Series(filtered, index=frame.index)
                values = (close - ls) / ls.replace(0.0, 1e-12)

        else:
            raise ValueError(f"AdaptiveFiltersCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=pd.Series(values.values if hasattr(values, "values") else values, index=frame.index),
            warmup=warmup,
        )
