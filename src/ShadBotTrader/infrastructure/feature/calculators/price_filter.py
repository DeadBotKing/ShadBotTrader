"""Price Filter features — نویززدایی قیمت (همه causal).

سه روش کاملاً causal برای فیلتر قیمت:

1. Kalman Filter (فیلتر کالمن)
   - بهترین روش online و real-time
   - هر کندل فقط از اطلاعات گذشته استفاده می‌کنه
   - خروجی: قیمت صاف‌شده + kalman_gain + kalman_residual

2. Causal Savitzky-Golay (نسخه causal)
   - فقط از پنجره گذشته استفاده می‌کنه (نه centered window)
   - پلینومیال fitting روی آخرین n کندل
   - خروجی: قیمت صاف‌شده + slope (جهت روند از دریواتیو)

3. DEMA / TEMA / ZLEMA (EMA پیشرفته)
   - Double/Triple EMA برای lag کمتر
   - Zero-Lag EMA برای حذف تأخیر

References:
  - Kalman: https://pyquantlab.medium.com/kalman-filter-adaptive
  - MQL5: https://www.mql5.com/en/articles/17273
  - SG filter: https://scienceaccess.blog/smooth-data-python-savitzky-golay
"""

from __future__ import annotations

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
# Kalman Filter (causal recursive — هیچ اطلاعات آینده‌ای استفاده نمی‌شه)
# ─────────────────────────────────────────────────────────────────────────────

def _kalman_filter(prices: np.ndarray, Q: float = 1e-3, R: float = 1e-2):
    """فیلتر کالمن scalar causal.

    State model: x[t] = x[t-1] + noise(Q)
    Observation: z[t] = x[t] + noise(R)

    Q: process noise — هرچه بزرگتر = فیلتر سریع‌تر (کمتر صاف)
    R: measurement noise — هرچه بزرگتر = فیلتر کندتر (بیشتر صاف)

    Returns:
        filtered: قیمت فیلترشده
        gains: Kalman gain در هر قدم (نشانگر uncertainty)
        residuals: z[t] - x_hat[t-1] (innovation / خطای پیش‌بینی)
    """
    n = len(prices)
    filtered = np.zeros(n)
    gains = np.zeros(n)
    residuals = np.zeros(n)

    # مقداردهی اولیه
    x_hat = prices[0]   # تخمین اولیه state
    P = 1.0              # تخمین اولیه covariance

    filtered[0] = x_hat
    gains[0] = 0.0
    residuals[0] = 0.0

    for t in range(1, n):
        # Prediction step
        x_pred = x_hat
        P_pred = P + Q

        # Innovation (خطا)
        innovation = prices[t] - x_pred
        residuals[t] = innovation

        # Kalman gain
        K = P_pred / (P_pred + R)
        gains[t] = K

        # Update step
        x_hat = x_pred + K * innovation
        P = (1.0 - K) * P_pred

        filtered[t] = x_hat

    return filtered, gains, residuals


# ─────────────────────────────────────────────────────────────────────────────
# Causal Savitzky-Golay (پنجره یک‌طرفه گذشته)
# ─────────────────────────────────────────────────────────────────────────────

def _causal_savgol(prices: np.ndarray, window: int = 11, polyorder: int = 2):
    """Savitzky-Golay فقط با داده گذشته (causal).

    به جای پنجره centered، از آخرین `window` کندل استفاده می‌کنه.
    برای هر نقطه یه پلینومیال روی [t-window+1 .. t] fit می‌کنه
    و مقدار پلینومیال در t رو برمی‌گردونه.

    Returns:
        smoothed: قیمت صاف‌شده
        slope: مشتق اول (جهت و شیب روند)
    """
    n = len(prices)
    smoothed = np.full(n, np.nan)
    slope = np.full(n, np.nan)

    for t in range(window - 1, n):
        segment = prices[t - window + 1: t + 1]
        x = np.arange(window, dtype=float)
        # Least squares polynomial fit
        coeffs = np.polyfit(x, segment, polyorder)
        # مقدار در آخرین نقطه (t)
        smoothed[t] = np.polyval(coeffs, window - 1)
        # مشتق اول در آخرین نقطه
        d_coeffs = np.polyder(coeffs)
        slope[t] = np.polyval(d_coeffs, window - 1)

    return smoothed, slope


# ─────────────────────────────────────────────────────────────────────────────
# Calculator class
# ─────────────────────────────────────────────────────────────────────────────

class PriceFilterCalculator(FeatureCalculator):
    """نویززدایی قیمت با روش‌های causal (همه بدون look-ahead).

    پارامترها:
      kind: نوع فیچر — یکی از:
        ── Kalman ──
        'kalman'          : قیمت فیلترشده با Kalman
        'kalman_gain'     : Kalman Gain (نزدیک 1 = نویز بالا، نزدیک 0 = روند پایدار)
        'kalman_residual' : خطای نوآوری Kalman (قیمت - تخمین قبلی)
        'kalman_distance' : فاصله نسبی قیمت از Kalman (close - kalman) / kalman
        ── Savitzky-Golay ──
        'sg_smooth'       : قیمت صاف‌شده با SG causal
        'sg_slope'        : شیب روند از SG (مثبت=صعود، منفی=نزول)
        'sg_distance'     : فاصله نسبی قیمت از SG
        ── EMA پیشرفته ──
        'dema'            : Double EMA (lag کمتر از EMA معمولی)
        'tema'            : Triple EMA (lag خیلی کم)
        'zlema'           : Zero-Lag EMA
        'dema_distance'   : فاصله نسبی قیمت از DEMA
      Q       : process noise Kalman (پیش‌فرض 1e-3)
      R       : measurement noise Kalman (پیش‌فرض 1e-2)
      window  : پنجره SG (پیش‌فرض 11، باید فرد باشه)
      polyorder: درجه پلینومیال SG (پیش‌فرض 2)
      period  : دوره EMA برای dema/tema/zlema (پیش‌فرض 14)
      column  : ستون قیمت (پیش‌فرض 'close')
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "kalman"))
        Q = float(params.get("Q", 1e-3))
        R = float(params.get("R", 1e-2))
        window = int(params.get("window", 11))
        polyorder = int(params.get("polyorder", 2))
        period = int(params.get("period", 14))
        column = str(params.get("column", "close"))

        frame = candle_frame(context)
        prices = frame[column].values.astype(float)
        close_series = frame[column]

        # ── Kalman ──────────────────────────────────────────────────────────
        if kind in ("kalman", "kalman_gain", "kalman_residual", "kalman_distance"):
            filtered, gains, residuals = _kalman_filter(prices, Q=Q, R=R)
            warmup = 1

            if kind == "kalman":
                values = pd.Series(filtered, index=frame.index)
            elif kind == "kalman_gain":
                values = pd.Series(gains, index=frame.index)
            elif kind == "kalman_residual":
                values = pd.Series(residuals, index=frame.index)
            else:  # kalman_distance
                kalman_s = pd.Series(filtered, index=frame.index)
                values = (close_series - kalman_s) / kalman_s.replace(0.0, 1e-12)

        # ── Savitzky-Golay (causal) ──────────────────────────────────────────
        elif kind in ("sg_smooth", "sg_slope", "sg_distance"):
            # حداقل پنجره باید از polyorder بیشتر باشه
            win = max(window, polyorder + 2)
            smoothed, slope = _causal_savgol(prices, window=win, polyorder=polyorder)
            warmup = win - 1

            if kind == "sg_smooth":
                values = pd.Series(smoothed, index=frame.index)
            elif kind == "sg_slope":
                values = pd.Series(slope, index=frame.index)
            else:  # sg_distance
                sg_s = pd.Series(smoothed, index=frame.index)
                values = (close_series - sg_s) / sg_s.replace(0.0, 1e-12)

        # ── EMA پیشرفته ──────────────────────────────────────────────────────
        elif kind in ("dema", "tema", "zlema", "dema_distance"):
            ema1 = close_series.ewm(span=period, adjust=False, min_periods=period).mean()
            warmup = period

            if kind == "dema":
                ema2 = ema1.ewm(span=period, adjust=False, min_periods=period).mean()
                values = 2.0 * ema1 - ema2

            elif kind == "tema":
                ema2 = ema1.ewm(span=period, adjust=False, min_periods=period).mean()
                ema3 = ema2.ewm(span=period, adjust=False, min_periods=period).mean()
                values = 3.0 * ema1 - 3.0 * ema2 + ema3
                warmup = period * 2

            elif kind == "zlema":
                # Zero-Lag EMA: EMA(close + (close - close.shift(period//2)))
                lag = period // 2
                adjusted = close_series + (close_series - close_series.shift(lag))
                values = adjusted.ewm(span=period, adjust=False, min_periods=period).mean()

            else:  # dema_distance
                ema2 = ema1.ewm(span=period, adjust=False, min_periods=period).mean()
                dema = 2.0 * ema1 - ema2
                values = (close_series - dema) / dema.replace(0.0, 1e-12)

        else:
            raise ValueError(f"PriceFilterCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
