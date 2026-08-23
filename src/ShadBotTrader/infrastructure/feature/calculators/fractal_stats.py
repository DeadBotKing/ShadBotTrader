"""Fractal & Statistical features (causal).

منابع:
  - Hurst (1951): R/S Analysis for long memory
  - Mandelbrot: Fractal Geometry & Financial Markets
  - Peters: "Chaos and Order in the Capital Markets" (1991)
  - Lo (1991): Modified R/S for short-range dependence
  - MDPI Fractal Dimension paper (2025)

فیچرهایی که پیاده‌سازی شدن:

1. Rolling Hurst Exponent (R/S method)
   H < 0.5 → mean-reverting  H ≈ 0.5 → random walk  H > 0.5 → trending
   روش: variance of lagged differences

2. Fractal Dimension (Higuchi method)
   D = 2 - H  (فراکتال بودن سری)

3. Shannon Entropy (Rolling)
   بی‌نظمی سری — انتروپی بالا = رندوم‌تر

4. Sample Entropy (Approximate)
   پیچیدگی سری — کمتر = قابل پیش‌بینی‌تر

5. Autocorrelation Feature
   همبستگی lag-1 و lag-5 — حافظه کوتاه‌مدت

6. Skewness & Kurtosis (Rolling)
   چولگی و کشیدگی توزیع بازده — برای مدل خطر

7. Realized Volatility (Parkinson)
   تخمین volatility از High-Low — دقیق‌تر از close-to-close

8. Garman-Klass Volatility
   بهترین تخمین volatility از OHLC
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


def _hurst_rs(series: np.ndarray) -> float:
    """Hurst exponent با روش variance of lagged differences (causal)."""
    n = len(series)
    if n < 8:
        return 0.5
    max_lag = max(2, n // 4)
    lags = range(2, min(max_lag, 20))
    tau = []
    for lag in lags:
        diff = series[lag:] - series[:-lag]
        s = np.std(diff)
        if s > 1e-12:
            tau.append(s)
        else:
            tau.append(1e-12)
    if len(tau) < 2:
        return 0.5
    log_lags = np.log(list(range(2, 2 + len(tau))))
    log_tau = np.log(tau)
    try:
        slope = np.polyfit(log_lags, log_tau, 1)[0]
        return float(slope)
    except Exception:
        return 0.5


def _shannon_entropy(returns: np.ndarray, bins: int = 10) -> float:
    """Shannon Entropy برای یه سری بازده."""
    if len(returns) < 4:
        return 0.0
    counts, _ = np.histogram(returns, bins=bins)
    probs = counts / counts.sum()
    probs = probs[probs > 0]
    return float(-np.sum(probs * np.log(probs + 1e-12)))


def _approx_sample_entropy(series: np.ndarray, m: int = 2, r_factor: float = 0.2) -> float:
    """Approximate Sample Entropy — پیچیدگی سری."""
    n = len(series)
    if n < 4:
        return 0.0
    r = r_factor * np.std(series)
    if r < 1e-12:
        return 0.0

    def count_matches(template_len):
        count = 0
        for i in range(n - template_len):
            template = series[i: i + template_len]
            for j in range(n - template_len):
                if i != j:
                    candidate = series[j: j + template_len]
                    if np.max(np.abs(template - candidate)) < r:
                        count += 1
        return count

    cm = count_matches(m)
    cm1 = count_matches(m + 1)
    if cm == 0:
        return 0.0
    return float(-math.log(cm1 / cm)) if cm1 > 0 else float(math.log(cm))


class FractalStatsCalculator(FeatureCalculator):
    """فیچرهای فراکتال و آماری سری زمانی (همه causal).

    پارامترها:
      kind: نوع فیچر — یکی از:
        ── فراکتال ──
        'hurst'             : Hurst Exponent rolling (R/S method)
        'fractal_dimension' : Fractal Dimension = 2 - Hurst
        ── آمار توصیفی ──
        'rolling_skew'      : چولگی بازده (skewness) — نامتقارنی
        'rolling_kurt'      : کشیدگی بازده (kurtosis) — دم‌پهن
        'rolling_entropy'   : Shannon Entropy بازده
        'autocorr_lag1'     : همبستگی خودی lag-1
        'autocorr_lag5'     : همبستگی خودی lag-5
        ── volatility پیشرفته ──
        'parkinson_vol'     : Parkinson Volatility (High-Low)
        'garman_klass_vol'  : Garman-Klass Volatility (OHLC)
        'yang_zhang_vol'    : Yang-Zhang Volatility (بهترین تخمین)
        'vol_of_vol'        : نوسان نوسان (VoV) — نوسان ATR
      period    : دوره rolling (پیش‌فرض 20)
      ret_period: دوره بازده (پیش‌فرض 1)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "hurst"))
        period = int(params.get("period", 20))

        frame = candle_frame(context)
        close = frame["close"]
        high = frame["high"]
        low = frame["low"]
        open_ = frame["open"]
        log_ret = np.log(close / close.shift(1))

        if kind in ("hurst", "fractal_dimension"):
            result = close.rolling(period, min_periods=period).apply(
                lambda x: _hurst_rs(x), raw=True
            )
            if kind == "fractal_dimension":
                result = 2.0 - result
            values = result
            warmup = period

        elif kind == "rolling_skew":
            values = log_ret.rolling(period, min_periods=period).skew()
            warmup = period

        elif kind == "rolling_kurt":
            values = log_ret.rolling(period, min_periods=period).kurt()
            warmup = period

        elif kind == "rolling_entropy":
            result = log_ret.rolling(period, min_periods=period).apply(
                lambda x: _shannon_entropy(x[~np.isnan(x)]), raw=True
            )
            values = result
            warmup = period

        elif kind == "autocorr_lag1":
            values = log_ret.rolling(period, min_periods=period).apply(
                lambda x: float(pd.Series(x).autocorr(lag=1)) if len(x) > 2 else 0.0,
                raw=False,
            )
            warmup = period + 1

        elif kind == "autocorr_lag5":
            win5 = max(period, 10)  # حداقل 10 نقطه برای lag-5
            values = log_ret.rolling(win5, min_periods=win5).apply(
                lambda x: float(pd.Series(x).autocorr(lag=5)) if len(x) > 6 else 0.0,
                raw=False,
            )
            warmup = win5 + 5

        elif kind == "parkinson_vol":
            # Parkinson (1980): σ² = (1/(4n×ln2)) × Σ(ln(H/L))²
            hl = np.log(high / low.replace(0.0, 1e-12))
            values = (hl ** 2).rolling(period, min_periods=period).mean().apply(
                lambda x: math.sqrt(x / (4.0 * math.log(2)))
            )
            warmup = period

        elif kind == "garman_klass_vol":
            # Garman-Klass (1980): ترکیب OHLC
            hl = np.log(high / low.replace(0.0, 1e-12))
            co = np.log(close / open_.replace(0.0, 1e-12))
            gk_sq = 0.5 * hl ** 2 - (2 * math.log(2) - 1) * co ** 2
            values = gk_sq.rolling(period, min_periods=period).mean().apply(
                lambda x: math.sqrt(max(x, 0.0))
            )
            warmup = period

        elif kind == "yang_zhang_vol":
            # Yang-Zhang (2000): بهترین تخمین — ترکیب overnight + open-to-close
            log_oc = np.log(close / open_.replace(0.0, 1e-12))
            log_co_prev = np.log(open_ / close.shift(1).replace(0.0, 1e-12))
            log_ho = np.log(high / open_.replace(0.0, 1e-12))
            log_lo = np.log(low / open_.replace(0.0, 1e-12))

            var_oc = log_oc.rolling(period, min_periods=period).var(ddof=1)
            var_co_prev = log_co_prev.rolling(period, min_periods=period).var(ddof=1)
            rs = (log_ho * (log_ho - log_oc) + log_lo * (log_lo - log_oc)).rolling(
                period, min_periods=period
            ).mean()
            k = 0.34 / (1.34 + (period + 1) / (period - 1))
            yz_var = var_co_prev + k * var_oc + (1.0 - k) * rs
            values = yz_var.apply(lambda x: math.sqrt(max(x, 0.0)))
            warmup = period + 1

        elif kind == "vol_of_vol":
            # نوسان نوسان: ATR از ATR — نشانگر ناپایداری بازار
            prev_close = close.shift(1)
            tr = pd.concat(
                [high - low,
                 (high - prev_close).abs(),
                 (low - prev_close).abs()],
                axis=1,
            ).max(axis=1)
            atr = tr.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            values = atr.rolling(period, min_periods=period).std(ddof=0)
            warmup = period * 2

        else:
            raise ValueError(f"FractalStatsCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
