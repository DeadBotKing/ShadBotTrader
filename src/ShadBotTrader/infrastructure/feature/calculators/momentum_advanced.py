"""Advanced Momentum features (causal).

اوسیلاتورهای پیشرفته که در سیستم‌های ML حرفه‌ای استفاده می‌شن:

- Stochastic RSI    : RSI داخل Stochastic — حساس‌تر
- MACD Histogram    : خط هیستوگرام MACD (شتاب تغییر)
- MACD Signal       : خط سیگنال MACD
- ROC               : Rate of Change (بازده درصدی)
- Momentum          : close[t] - close[t-n]
- TSI               : True Strength Index (دو بار smooth)
- Awesome Oscillator: AO ← میانگین (high+low)/2 در دو بازه
- Vortex Indicator  : VM+ و VM- — قوت حرکت صعودی/نزولی

References:
  - finta indicators: https://pypi.org/project/finta/
  - DRL gold bot: https://github.com/zero-was-here/tradingbot
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


def _true_range(frame: pd.DataFrame) -> pd.Series:
    prev_close = frame["close"].shift(1)
    return pd.concat(
        [frame["high"] - frame["low"],
         (frame["high"] - prev_close).abs(),
         (frame["low"] - prev_close).abs()],
        axis=1,
    ).max(axis=1)


class MomentumAdvancedCalculator(FeatureCalculator):
    """اوسیلاتورهای پیشرفته مومنتوم (همه causal).

    پارامترها:
      kind: نوع فیچر — یکی از:
        'stoch_rsi'    : Stochastic RSI (0-100)
        'macd_hist'    : MACD Histogram (شتاب)
        'macd_signal'  : MACD Signal line
        'roc'          : Rate of Change (%)
        'momentum'     : Momentum خام
        'tsi'          : True Strength Index
        'awesome_osc'  : Awesome Oscillator
        'vortex_plus'  : Vortex +VM
        'vortex_minus' : Vortex -VM
        'vortex_diff'  : +VM - (-VM) = جهت حرکت
      period     : دوره اصلی (پیش‌فرض 14)
      fast       : دوره سریع MACD (پیش‌فرض 12)
      slow       : دوره کند MACD (پیش‌فرض 26)
      signal     : دوره signal MACD (پیش‌فرض 9)
    """

    def compute(self, definition: FeatureDefinition, context: FeatureInputContext) -> FeatureResult:
        params = definition.parameters
        kind = str(params.get("kind", "stoch_rsi"))
        period = int(params.get("period", 14))
        fast = int(params.get("fast", 12))
        slow = int(params.get("slow", 26))
        signal_period = int(params.get("signal", 9))

        frame = candle_frame(context)
        close = frame["close"]
        high = frame["high"]
        low = frame["low"]

        if kind == "stoch_rsi":
            # Stochastic RSI: RSI رو داخل Stochastic می‌ذاریم
            delta = close.diff()
            gain = delta.clip(lower=0.0)
            loss = -delta.clip(upper=0.0)
            avg_gain = gain.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            avg_loss = loss.ewm(alpha=1.0 / period, adjust=False, min_periods=period).mean()
            rs = avg_gain / avg_loss.replace(0.0, 1e-12)
            rsi = 100.0 - (100.0 / (1.0 + rs))
            rsi_min = rsi.rolling(period, min_periods=period).min()
            rsi_max = rsi.rolling(period, min_periods=period).max()
            denom = (rsi_max - rsi_min).replace(0.0, 1e-12)
            values = 100.0 * (rsi - rsi_min) / denom
            warmup = period * 2

        elif kind in ("macd_hist", "macd_signal"):
            ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
            ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
            macd_line = ema_fast - ema_slow
            signal_line = macd_line.ewm(span=signal_period, adjust=False, min_periods=signal_period).mean()
            warmup = slow + signal_period - 1
            if kind == "macd_hist":
                values = macd_line - signal_line
            else:
                values = signal_line

        elif kind == "roc":
            # Rate of Change: (close[t] / close[t-n] - 1) × 100
            values = close.pct_change(period) * 100.0
            warmup = period

        elif kind == "momentum":
            # Momentum خام: close[t] - close[t-n]
            values = close.diff(period)
            warmup = period

        elif kind == "tsi":
            # True Strength Index: double-smoothed momentum
            # TSI = 100 × EMA(EMA(Δclose)) / EMA(EMA(|Δclose|))
            fast_tsi = int(params.get("fast", 25))
            slow_tsi = int(params.get("slow", 13))
            delta = close.diff()
            smoothed1 = delta.ewm(span=fast_tsi, adjust=False, min_periods=fast_tsi).mean()
            smoothed2 = smoothed1.ewm(span=slow_tsi, adjust=False, min_periods=slow_tsi).mean()
            abs_smoothed1 = delta.abs().ewm(span=fast_tsi, adjust=False, min_periods=fast_tsi).mean()
            abs_smoothed2 = abs_smoothed1.ewm(span=slow_tsi, adjust=False, min_periods=slow_tsi).mean()
            values = 100.0 * smoothed2 / abs_smoothed2.replace(0.0, 1e-12)
            warmup = fast_tsi + slow_tsi

        elif kind == "awesome_osc":
            # Awesome Oscillator: SMA(5) - SMA(34) از midpoint
            midpoint = (high + low) / 2.0
            ao_fast = int(params.get("ao_fast", 5))
            ao_slow = int(params.get("ao_slow", 34))
            values = (midpoint.rolling(ao_fast, min_periods=ao_fast).mean()
                      - midpoint.rolling(ao_slow, min_periods=ao_slow).mean())
            warmup = ao_slow

        elif kind in ("vortex_plus", "vortex_minus", "vortex_diff"):
            # Vortex Indicator
            tr = _true_range(frame)
            vm_plus = (high - low.shift(1)).abs()
            vm_minus = (low - high.shift(1)).abs()
            sum_tr = tr.rolling(period, min_periods=period).sum().replace(0.0, 1e-12)
            vp = vm_plus.rolling(period, min_periods=period).sum() / sum_tr
            vm = vm_minus.rolling(period, min_periods=period).sum() / sum_tr
            warmup = period
            if kind == "vortex_plus":
                values = vp
            elif kind == "vortex_minus":
                values = vm
            else:
                values = vp - vm

        else:
            raise ValueError(f"MomentumAdvancedCalculator: kind نامعتبر: {kind!r}")

        return result_from_series(
            feature_id=definition.feature_id.value,
            context=context,
            values=values,
            warmup=warmup,
        )
