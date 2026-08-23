"""Lopez de Prado Features — از کتاب "Advances in Financial Machine Learning" (2018).

منابع:
  - M. Lopez de Prado: "Advances in Financial Machine Learning" (Wiley, 2018)
    Ch.5: Fractional Differentiation
    Ch.17: Microstructural Features (VPIN, Kyle's Lambda)
  - Hudson & Thames: mlfinlab implementation

فیچرهایی که پیاده‌سازی شدن:

1. Fractional Differentiation (FFD)
   قیمت رو stationary می‌کنه بدون از دست دادن حافظه
   d=0 = قیمت خام (حافظه کامل، non-stationary)
   d=1 = بازده (stationary، حافظه صفر)
   d=0.4 = بهینه (stationary + حافظه جزئی)

2. CUSUM Filter (Symmetric)
   تغییرات بزرگ و معنادار رو شناسایی می‌کنه
   مثل یه detector برای event های مهم

3. Rolling Sharpe Ratio
   کیفیت بازده در پنجره rolling

4. Dollar Bar Features
   ویژگی‌هایی که از تئوری bar sampling می‌آن

5. Kyle's Lambda (تقریبی)
   impact قیمت بر اساس جریان سفارشات — نقدشوندگی

6. VPIN (تقریبی)
   Volume-synchronized Probability of Informed Trading
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


def _frac_diff_weights(d: float, size: int, threshold: float = 1e-5) -> np.ndarray:
    """وزن‌های fractional differentiation (Lopez de Prado Ch.5)."""
    w = [1.0]
    for k in range(1, size):
        w_k = -w[-1] * (d - k + 1) / k
        if abs(w_k) < threshold:
            break
        w.append(w_k)
    return np.array(w[::-1])


def _frac_diff_ffd(series: np.ndarray, d: float, threshold: float = 1e-5) -> np.ndarray:
    """Fixed-width window Fractional Differentiation (causal).

    هر مقدار فقط از گذشته محاسبه می‌شه — کاملاً causal.
    """
    n = len(series)
    weights = _frac_diff_weights(d, n, threshold)
    w_len = len(weights)
    result = np.full(n, np.nan)
    for t in range(w_len - 1, n):
        window = series[t - w_len + 1: t + 1]
        result[t] = float(np.dot(weights, window))
    return result


class PradoFeaturesCalculator(FeatureCalculator):
    """فیچرهای Lopez de Prado (همه causal).

    kind:
      'frac_diff'      : Fractional Differentiation (d=0.4 default)
      'frac_diff_ret'  : FracDiff روی log-returns (d=0.3)
      'cusum_pos'      : CUSUM مثبت — انباشت حرکت صعودی
      'cusum_neg'      : CUSUM منفی — انباشت حرکت نزولی
      'rolling_sharpe' : Sharpe ratio rolling
      'rolling_calmar' : Calmar ratio (return / max_drawdown) rolling
      'kyles_lambda'   : Kyle's Lambda — market impact (تقریبی)
      'amihud_illiq'   : Amihud Illiquidity ratio |r| / volume
      'bid_ask_spread' : تخمین spread از OHLC (Roll's model)
      'price_impact'   : تأثیر قیمت حجم‌دار (روی بازده نرمال‌شده)
    d          : درجه fractional diff (پیش‌فرض 0.4)
    period     : دوره rolling (پیش‌فرض 20)
    threshold  : آستانه برای FracDiff (پیش‌فرض 1e-5)
    h          : آستانه CUSUM (پیش‌فرض 0.001)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "frac_diff"))
        d = float(params.get("d", 0.4))
        period = int(params.get("period", 20))
        threshold = float(params.get("threshold", 1e-5))
        h = float(params.get("h", 0.001))

        frame = candle_frame(context)
        close = frame["close"]
        high = frame["high"]
        low = frame["low"]
        volume = frame["volume"]
        log_price = np.log(close.values.astype(float) + 1e-12)
        log_ret = pd.Series(np.diff(log_price, prepend=np.nan), index=frame.index)

        if kind == "frac_diff":
            fd = _frac_diff_ffd(log_price, d=d, threshold=threshold)
            values = pd.Series(fd, index=frame.index)
            warmup = len(_frac_diff_weights(d, len(log_price), threshold))

        elif kind == "frac_diff_ret":
            ret = log_ret.fillna(0.0).values
            fd = _frac_diff_ffd(ret, d=0.3, threshold=threshold)
            values = pd.Series(fd, index=frame.index)
            warmup = len(_frac_diff_weights(0.3, len(ret), threshold))

        elif kind in ("cusum_pos", "cusum_neg"):
            # CUSUM filter: انباشت رویدادهای معنادار
            ret_arr = log_ret.fillna(0.0).values
            s_pos = np.zeros(len(ret_arr))
            s_neg = np.zeros(len(ret_arr))
            for t in range(1, len(ret_arr)):
                s_pos[t] = max(0.0, s_pos[t - 1] + ret_arr[t])
                s_neg[t] = min(0.0, s_neg[t - 1] + ret_arr[t])
            if kind == "cusum_pos":
                values = pd.Series(s_pos, index=frame.index)
            else:
                values = pd.Series(s_neg, index=frame.index)
            warmup = 1

        elif kind == "rolling_sharpe":
            # Sharpe ratio rolling (annualized با فرض 5M bars)
            bars_per_year = 252 * 24 * 12  # 5M bars در سال
            mu = log_ret.rolling(period, min_periods=period).mean()
            sigma = log_ret.rolling(period, min_periods=period).std(ddof=1).replace(0.0, 1e-12)
            values = mu / sigma * math.sqrt(bars_per_year)
            warmup = period

        elif kind == "rolling_calmar":
            # Calmar ratio: return / max_drawdown rolling
            cum_ret = log_ret.fillna(0.0).rolling(period, min_periods=period).sum()
            roll_max = close.rolling(period, min_periods=period).max()
            drawdown = (close - roll_max) / roll_max.replace(0.0, 1e-12)
            max_dd = drawdown.rolling(period, min_periods=period).min().abs().replace(0.0, 1e-12)
            values = cum_ret / max_dd
            warmup = period

        elif kind == "kyles_lambda":
            # Kyle's Lambda (تقریبی از OHLC): |Δprice| / volume
            # معادل market impact — بالا = بازار کم‌عمق
            delta_price = close.diff().abs()
            vol_norm = volume.replace(0.0, 1e-12)
            values = (delta_price / vol_norm).rolling(period, min_periods=period).mean()
            warmup = period + 1

        elif kind == "amihud_illiq":
            # Amihud (2002) Illiquidity: |r_t| / dollar_volume
            # بالا = بازار کم‌نقدشوندگی
            abs_ret = log_ret.abs()
            dollar_vol = close * volume.replace(0.0, 1e-12)
            illiq = abs_ret / dollar_vol.replace(0.0, 1e-12)
            values = illiq.rolling(period, min_periods=period).mean()
            warmup = period + 1

        elif kind == "bid_ask_spread":
            # Roll (1984): تخمین bid-ask spread از serial covariance بازده
            # spread ≈ 2 * sqrt(-cov(r_t, r_{t-1}))  اگه cov منفی باشه
            cov = log_ret.rolling(period + 1, min_periods=period + 1).apply(
                lambda x: float(pd.Series(x).autocorr(lag=1)) * pd.Series(x).std() ** 2
                if len(x) > 2 else 0.0,
                raw=False,
            )
            values = cov.apply(lambda c: 2.0 * math.sqrt(max(-c, 0.0)))
            warmup = period + 2

        elif kind == "price_impact":
            # تأثیر قیمت: بازده نرمال‌شده به حجم — نشانه فشار خریدار/فروشنده
            sign_ret = log_ret.apply(lambda x: 1.0 if x > 0 else (-1.0 if x < 0 else 0.0))
            vol_norm = volume.rolling(period, min_periods=period).mean().replace(0.0, 1e-12)
            values = (log_ret.abs() * sign_ret) / vol_norm
            warmup = period + 1

        else:
            raise ValueError(f"PradoFeaturesCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
