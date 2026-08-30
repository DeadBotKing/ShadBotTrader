"""فاز ۹۴ — فیچرهای «موقعیت قیمت» — به مدل می‌گوید قیمت کجاست.

این فیچرها scale-invariant هستند (نسبت‌اند نه مطلق) و بعد از minmax
هم معنی‌شان حفظ می‌شود:
  close_div_sma_N = 1.05 یعنی قیمت ۵٪ بالاتر از SMA(N)

مدل رنج قبلاً برای هر ورودی یک خروجی ثابت می‌داد (±0.06%) چون بعد از
minmax هیچ اطلاعی دربارهٔ «قیمت الان کجاست» نداشت. این فیچرها آن
اطلاعات را می‌دهند.
"""

from __future__ import annotations

from typing import Any, Optional

import numpy as np
import pandas as pd

from ShadBotTrader.domain.feature.feature_definition import FeatureDefinition, FeatureId
from ShadBotTrader.domain.feature.feature_result import FeaturePoint, FeatureResult
from ShadBotTrader.domain.feature.feature_types import FeatureType
from ShadBotTrader.domain.feature.ports import FeatureCalculator


class PriceContextCalculator(FeatureCalculator):
    """موقعیت قیمت نسبت به میانگین‌های مختلف — نسبی و scale-invariant."""

    PERIODS = (20, 50)

    def compute(self, definition: FeatureDefinition, context: Any) -> FeatureResult:
        params = definition.parameters
        period = int(params.get("period", 50))
        candles = context.candles

        if len(candles) < period:
            return FeatureResult(
                feature_id=definition.feature_id,
                values=[None] * len(candles),
                warmup=period,
            )

        close = np.array([float(c.close.amount) for c in candles])
        sma = pd.Series(close).rolling(period).mean().values

        # نسبت: 1.0 = روی میانگین · >1.0 = بالاتر · <1.0 = پایین‌تر
        ratio = np.where(sma > 0, close / sma, None)

        values: list[Optional[float]] = []
        for i in range(len(candles)):
            v = ratio[i] if i < len(ratio) else None
            values.append(float(v) if v is not None and not np.isnan(v) else None)

        points = []
        for i, candle in enumerate(candles):
            v = values[i] if i < len(values) else None
            points.append(FeaturePoint(timestamp=candle.open_time, value=v))
        return FeatureResult(
            feature_id=definition.feature_id.value,
            points=points,
            warmup=period,
        )

    @staticmethod
    def definitions() -> list[FeatureDefinition]:
        """همهٔ تعریف‌های این خانواده — در standard_catalog فراخوانی می‌شود."""
        return [
            FeatureDefinition(
                feature_id=FeatureId(f"close_div_sma_{p}"),
                name=f"Close / SMA {p} (position ratio)",
                feature_type=FeatureType.MOMENTUM,
                parameters={"period": p},
                lookback=p,
                family="price_context",
                description=(
                    f"نسبت قیمت به SMA {p} — scale-invariant، "
                    "به مدل می‌گوید قیمت کجاست (بدون minmax از دست رفتن مقیاس)"
                ),
            )
            for p in PriceContextCalculator.PERIODS
        ]
