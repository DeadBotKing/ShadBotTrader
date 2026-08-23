"""Ehlers Cycle & DSP features (causal).

از کتاب‌های John Ehlers:
  "Rocket Science for Traders" (2001)
  "Cybernetic Analysis for Stocks and Futures" (2004)
  "Cycle Analytics for Traders" (2013)
  TASC Magazine June 2025 (Cybernetic Oscillator)

این فیچرها بازار رو از دیدگاه signal processing نگاه می‌کنن:

1. Roofing Filter
   High-pass + SuperSmoother: فقط سیکل‌های بازار رو نگه می‌داره
   نویز کوتاه‌مدت و ترند بلندمدت رو هر دو حذف می‌کنه

2. Cyber Cycle
   فاز سیکل بازار — وقتی به اشباع رسیده نشون می‌ده

3. Fisher Transform
   قیمت رو به توزیع Gaussian تبدیل می‌کنه
   نقاط اشباع خرید/فروش خیلی واضح‌تر می‌شن

4. Inverse Fisher Transform (روی RSI)
   RSI رو به بازه‌ای با توزیع Gaussian می‌بره

5. Center of Gravity (CoG)
   مرکز ثقل قیمت — پیش‌بینی نقاط بازگشت

6. Laguerre RSI
   RSI با فیلتر Laguerre — lag خیلی کم
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


def _highpass_filter(prices: np.ndarray, period: int = 48) -> np.ndarray:
    """Ehlers 2-pole High-Pass Filter (causal).

    حرکات بلندمدت (ترند) رو حذف می‌کنه، سیکل‌های کوتاه رو نگه می‌داره.
    """
    n = len(prices)
    result = np.full(n, 0.0)
    sq2 = math.sqrt(2.0)
    a1 = math.exp(-sq2 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(math.degrees(sq2 * math.pi / period) * math.pi / 180.0)

    # فرمول Ehlers: c1 = (1+c2-c3)/4  c2=b1  c3=-a1²
    c2 = b1
    c3 = -(a1 ** 2)
    c1 = (1.0 + c2 - c3) / 4.0

    for t in range(2, n):
        result[t] = (
            c1 * (prices[t] - 2.0 * prices[t - 1] + prices[t - 2])
            + c2 * result[t - 1]
            + c3 * result[t - 2]
        )
    return result


def _supersmoother_arr(prices: np.ndarray, period: int = 10) -> np.ndarray:
    """Ehlers SuperSmoother (2-pole) — نسخه array برای internal use."""
    n = len(prices)
    result = np.full(n, np.nan)
    sq2 = math.sqrt(2.0)
    a1 = math.exp(-sq2 * math.pi / period)
    b1 = 2.0 * a1 * math.cos(math.radians(sq2 * 180.0 / period))
    c2, c3 = b1, -(a1 ** 2)
    c1 = 1.0 - c2 - c3

    for t in range(2, n):
        mid = (prices[t] + prices[t - 1]) / 2.0
        p1 = result[t - 1] if not np.isnan(result[t - 1]) else prices[t - 1]
        p2 = result[t - 2] if not np.isnan(result[t - 2]) else prices[t - 2]
        result[t] = c1 * mid + c2 * p1 + c3 * p2

    return result


class EhlersCycleCalculator(FeatureCalculator):
    """فیچرهای DSP و سیکل Ehlers (همه causal).

    پارامترها:
      kind: نوع فیچر — یکی از:
        'roofing_filter'  : Roofing Filter (detrended, denoised)
        'cyber_cycle'     : Cyber Cycle oscillator
        'fisher_transform': Fisher Transform قیمت
        'inverse_fisher'  : Inverse Fisher Transform روی RSI(14)
        'center_of_gravity': Center of Gravity oscillator
        'laguerre_rsi'    : Laguerre RSI (lag کم‌تر)
        'cybernetic_osc'  : Cybernetic Oscillator (Ehlers 2025)
      period     : دوره SuperSmoother / Cyber Cycle (پیش‌فرض 10)
      hp_period  : دوره High-Pass برای Roofing (پیش‌فرض 48)
      cog_period : دوره Center of Gravity (پیش‌فرض 10)
      gamma      : پارامتر Laguerre (پیش‌فرض 0.5)
      rsi_period : دوره RSI برای Inverse Fisher (پیش‌فرض 14)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "roofing_filter"))
        period = int(params.get("period", 10))
        hp_period = int(params.get("hp_period", 48))
        cog_period = int(params.get("cog_period", 10))
        gamma = float(params.get("gamma", 0.5))
        rsi_period = int(params.get("rsi_period", 14))

        frame = candle_frame(context)
        close = frame["close"]
        prices = close.values.astype(float)
        n = len(prices)

        if kind == "roofing_filter":
            # High-Pass → SuperSmoother: فقط سیکل‌های بازار
            hp = _highpass_filter(prices, period=hp_period)
            roofed = _supersmoother_arr(hp, period=period)
            values = pd.Series(roofed, index=frame.index)
            warmup = max(period, hp_period)

        elif kind == "cyber_cycle":
            # Cyber Cycle: از "Cybernetic Analysis" Ehlers
            # روی Roofing Filter اعمال می‌شه
            hp = _highpass_filter(prices, period=hp_period)
            smooth = _supersmoother_arr(hp, period=period)

            result = np.full(n, 0.0)
            sq2 = math.sqrt(2.0)
            a1 = math.exp(-sq2 * math.pi / period)
            b1 = 2.0 * a1 * math.cos(math.radians(sq2 * 180.0 / period))
            c2, c3 = b1, -(a1 ** 2)
            c1 = (1.0 - c2 - c3) / 4.0

            for t in range(2, n):
                p = smooth[t] if not np.isnan(smooth[t]) else 0.0
                p1 = smooth[t - 1] if not np.isnan(smooth[t - 1]) else 0.0
                p2 = smooth[t - 2] if not np.isnan(smooth[t - 2]) else 0.0
                result[t] = (
                    c1 * (p - 2.0 * p1 + p2)
                    + c2 * result[t - 1]
                    + c3 * result[t - 2]
                )

            values = pd.Series(result, index=frame.index)
            warmup = max(period, hp_period) + 2

        elif kind == "fisher_transform":
            # Fisher Transform: قیمت رو به Gaussian تبدیل می‌کنه
            # value = (close - lowest) / (highest - lowest) × 2 - 1
            # Fisher = 0.5 × ln((1+v)/(1-v))
            roll_high = close.rolling(period, min_periods=period).max()
            roll_low = close.rolling(period, min_periods=period).min()
            denom = (roll_high - roll_low).replace(0.0, 1e-12)
            value = 2.0 * ((close - roll_low) / denom) - 1.0
            # clamp به [-0.999, 0.999] برای log پایدار
            value = value.clip(-0.999, 0.999)
            fisher = 0.5 * np.log((1.0 + value) / (1.0 - value))
            values = fisher
            warmup = period

        elif kind == "inverse_fisher":
            # Inverse Fisher Transform روی RSI
            delta = close.diff()
            gain = delta.clip(lower=0.0)
            loss = -delta.clip(upper=0.0)
            ag = gain.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
            al = loss.ewm(alpha=1.0 / rsi_period, adjust=False, min_periods=rsi_period).mean()
            rsi = 100.0 - (100.0 / (1.0 + ag / al.replace(0.0, 1e-12)))
            # RSI رو به [-1, 1] می‌بریم
            x = 0.1 * (rsi - 50.0)
            exp2x = np.exp(2.0 * x)
            ift = (exp2x - 1.0) / (exp2x + 1.0)
            values = ift
            warmup = rsi_period + 1

        elif kind == "center_of_gravity":
            # Center of Gravity (Ehlers) — نقاط بازگشت
            # CoG = -Σ(price[i] × (i+1)) / Σ(price[i])
            result = np.full(n, np.nan)
            for t in range(cog_period - 1, n):
                num = 0.0
                den = 0.0
                for i in range(cog_period):
                    p = prices[t - i]
                    num += p * (i + 1)
                    den += p
                result[t] = -num / den if abs(den) > 1e-12 else 0.0
            values = pd.Series(result, index=frame.index)
            warmup = cog_period

        elif kind == "laguerre_rsi":
            # Laguerre RSI (Ehlers) — lag کمتر از RSI معمولی
            L0 = np.zeros(n)
            L1 = np.zeros(n)
            L2 = np.zeros(n)
            L3 = np.zeros(n)
            result = np.full(n, np.nan)

            L0[0] = prices[0]
            for t in range(1, n):
                L0[t] = (1.0 - gamma) * prices[t] + gamma * L0[t - 1]
                L1[t] = -gamma * L0[t] + L0[t - 1] + gamma * L1[t - 1]
                L2[t] = -gamma * L1[t] + L1[t - 1] + gamma * L2[t - 1]
                L3[t] = -gamma * L2[t] + L2[t - 1] + gamma * L3[t - 1]

                cu = 0.0
                cd = 0.0
                if L0[t] >= L1[t]:
                    cu += L0[t] - L1[t]
                else:
                    cd += L1[t] - L0[t]
                if L1[t] >= L2[t]:
                    cu += L1[t] - L2[t]
                else:
                    cd += L2[t] - L1[t]
                if L2[t] >= L3[t]:
                    cu += L2[t] - L3[t]
                else:
                    cd += L3[t] - L2[t]

                if (cu + cd) > 1e-12:
                    result[t] = cu / (cu + cd)
                else:
                    result[t] = 0.5

            values = pd.Series(result, index=frame.index)
            warmup = 4

        elif kind == "cybernetic_osc":
            # Cybernetic Oscillator (Ehlers, TASC June 2025)
            # HP → SS → normalize by RMS
            rms_period = int(params.get("rms_period", 50))
            hp = _highpass_filter(prices, period=hp_period)
            ss = _supersmoother_arr(hp, period=period)
            ss_series = pd.Series(ss, index=frame.index).fillna(0.0)
            rms = ss_series.rolling(rms_period, min_periods=rms_period).apply(
                lambda x: math.sqrt(np.sum(x ** 2) / len(x)), raw=True
            ).replace(0.0, 1e-12)
            values = ss_series / rms
            warmup = max(period, hp_period) + rms_period

        else:
            raise ValueError(f"EhlersCycleCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=pd.Series(values.values if hasattr(values, "values") else values,
                             index=frame.index),
            warmup=warmup,
        )
