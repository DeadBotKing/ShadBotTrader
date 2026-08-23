"""Volume Analysis features (causal).

فیچرهای حجم‌محور که در بهترین سیستم‌های ML trading استفاده می‌شن:

- OBV  (On-Balance Volume) — تجمیع جریان حجم
- MFI  (Money Flow Index) — RSI حجم‌دار
- CMF  (Chaikin Money Flow) — فشار خرید/فروش بر اساس حجم
- CCI  (Commodity Channel Index) — انحراف از میانگین نرمال‌شده
- Williams %R — اشباع با high/low پنجره
- Force Index — ترکیب قدرت قیمت × حجم
- Volume Rate of Change — شتاب حجم
- Volume Z-Score — سطح حجم نسبت به میانگین

References:
  - finta: https://pypi.org/project/finta/
  - mql5: https://www.mql5.com/en/blogs/post/767489
  - 140+ features repo: https://github.com/zero-was-here/tradingbot
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


class VolumeAnalysisCalculator(FeatureCalculator):
    """فیچرهای تحلیل حجم (همه causal).

    پارامترها:
      kind: نوع فیچر — یکی از:
        'obv'            : On-Balance Volume (تجمیع)
        'obv_slope'      : شیب OBV — جریان حجم تازه
        'mfi'            : Money Flow Index (0-100)
        'cmf'            : Chaikin Money Flow (-1 تا +1)
        'cci'            : Commodity Channel Index
        'williams_r'     : Williams %R (-100 تا 0)
        'force_index'    : Elder's Force Index
        'volume_roc'     : Volume Rate of Change
        'volume_zscore'  : Z-Score حجم در پنجره rolling
        'volume_ratio'   : نسبت حجم به میانگین بلندمدت
      period: دوره (پیش‌فرض 14)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "obv"))
        period = int(params.get("period", 14))

        frame = candle_frame(context)
        high = frame["high"]
        low = frame["low"]
        close = frame["close"]
        volume = frame["volume"]
        typical = (high + low + close) / 3.0

        if kind == "obv":
            # On-Balance Volume: حجم رو بر اساس جهت حرکت قیمت جمع می‌کنه
            direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
            values = (direction * volume).cumsum()
            warmup = 1

        elif kind == "obv_slope":
            direction = close.diff().apply(lambda x: 1 if x > 0 else (-1 if x < 0 else 0))
            obv = (direction * volume).cumsum()
            values = obv.diff(period)
            warmup = period + 1

        elif kind == "mfi":
            # Money Flow Index: RSI ولی با حجم وزن‌دار
            money_flow = typical * volume
            positive_mf = money_flow.where(typical > typical.shift(1), 0.0)
            negative_mf = money_flow.where(typical < typical.shift(1), 0.0)
            pos_sum = positive_mf.rolling(period, min_periods=period).sum()
            neg_sum = negative_mf.rolling(period, min_periods=period).sum()
            mfr = pos_sum / neg_sum.replace(0.0, 1e-12)
            values = 100.0 - (100.0 / (1.0 + mfr))
            warmup = period + 1

        elif kind == "cmf":
            # Chaikin Money Flow: (close - low - high + close) / (high - low) × volume
            clv = ((close - low) - (high - close)) / (high - low).replace(0.0, 1e-12)
            cmf_num = (clv * volume).rolling(period, min_periods=period).sum()
            cmf_den = volume.rolling(period, min_periods=period).sum().replace(0.0, 1e-12)
            values = cmf_num / cmf_den
            warmup = period

        elif kind == "cci":
            # Commodity Channel Index
            mean_deviation = (typical - typical.rolling(period, min_periods=period).mean()).abs()
            mean_dev_rolling = mean_deviation.rolling(period, min_periods=period).mean().replace(0.0, 1e-12)
            tp_mean = typical.rolling(period, min_periods=period).mean()
            values = (typical - tp_mean) / (0.015 * mean_dev_rolling)
            warmup = period

        elif kind == "williams_r":
            # Williams %R: موقعیت close نسبت به high/low پنجره (0 تا -100)
            highest_high = high.rolling(period, min_periods=period).max()
            lowest_low = low.rolling(period, min_periods=period).min()
            denom = (highest_high - lowest_low).replace(0.0, 1e-12)
            values = -100.0 * (highest_high - close) / denom
            warmup = period

        elif kind == "force_index":
            # Elder's Force Index: change × volume
            values = close.diff() * volume
            warmup = 1

        elif kind == "volume_roc":
            # Volume Rate of Change: چقدر حجم تغییر کرده
            values = volume.pct_change(period)
            warmup = period

        elif kind == "volume_zscore":
            # Z-Score حجم: حجم الان نسبت به میانگین و انحراف معیار
            vol_mean = volume.rolling(period, min_periods=period).mean()
            vol_std = volume.rolling(period, min_periods=period).std(ddof=0).replace(0.0, 1e-12)
            values = (volume - vol_mean) / vol_std
            warmup = period

        elif kind == "volume_ratio":
            # نسبت حجم کوتاه‌مدت به بلندمدت
            short_avg = volume.rolling(period, min_periods=period).mean()
            long_avg = volume.rolling(period * 3, min_periods=period * 3).mean().replace(0.0, 1e-12)
            values = short_avg / long_avg
            warmup = period * 3

        else:
            raise ValueError(f"VolumeAnalysisCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
