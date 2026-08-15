"""The standard FX feature set (v1), built from the legacy knowledge."""

from __future__ import annotations

from typing import List

from ShadBotTrader.domain.feature.feature_definition import (
    FeatureDefinition,
    FeatureId,
)
from ShadBotTrader.domain.feature.feature_set import FeatureSet, FeatureSetVersion
from ShadBotTrader.domain.feature.feature_types import (
    FeatureType,
    FeatureValueType,
)


def standard_feature_set_v1() -> FeatureSet:
    """Return ``FXTradingFeatureSetV1``.

    Mirrors the indicator families the legacy FeatureEngineering module
    computed (SMA/EMA/RSI/ATR/MACD/Bollinger/Stochastic) as clean,
    causal, parameterised feature definitions.
    """
    definitions: List[FeatureDefinition] = [
        FeatureDefinition(
            feature_id=FeatureId("sma_20"),
            name="SMA 20",
            feature_type=FeatureType.TREND,
            value_type=FeatureValueType.SCALAR,
            parameters={"period": 20},
            lookback=19,
            computation_version="1",
            description="Simple moving average of close over 20 candles",
        ),
        FeatureDefinition(
            feature_id=FeatureId("ema_50"),
            name="EMA 50",
            feature_type=FeatureType.TREND,
            value_type=FeatureValueType.SCALAR,
            parameters={"period": 50},
            lookback=49,
            computation_version="1",
            description="Exponential moving average of close over 50 candles",
        ),
        FeatureDefinition(
            feature_id=FeatureId("rsi_14"),
            name="RSI 14",
            feature_type=FeatureType.MOMENTUM,
            value_type=FeatureValueType.SCALAR,
            parameters={"period": 14},
            lookback=14,
            computation_version="1",
            description="Wilder RSI over 14 candles",
        ),
        FeatureDefinition(
            feature_id=FeatureId("atr_14"),
            name="ATR 14",
            feature_type=FeatureType.VOLATILITY,
            value_type=FeatureValueType.SCALAR,
            parameters={"period": 14},
            lookback=14,
            computation_version="1",
            description="Wilder average true range over 14 candles",
        ),
        FeatureDefinition(
            feature_id=FeatureId("macd_12_26_9"),
            name="MACD 12/26/9",
            feature_type=FeatureType.MOMENTUM,
            value_type=FeatureValueType.SCALAR,
            parameters={"fast": 12, "slow": 26, "signal": 9},
            lookback=33,
            computation_version="1",
            description="MACD line (12/26/9)",
        ),
        FeatureDefinition(
            feature_id=FeatureId("bollinger_20_2"),
            name="Bollinger %B (20, 2)",
            feature_type=FeatureType.STATISTICAL,
            value_type=FeatureValueType.SCALAR,
            parameters={"period": 20, "num_std": 2.0},
            lookback=19,
            computation_version="1",
            description="Bollinger %B position over 20 candles, 2 std",
        ),
        FeatureDefinition(
            feature_id=FeatureId("stochastic_14"),
            name="Stochastic %K 14",
            feature_type=FeatureType.MOMENTUM,
            value_type=FeatureValueType.SCALAR,
            parameters={"period": 14},
            lookback=13,
            computation_version="1",
            description="Stochastic %K over 14 candles",
        ),
        FeatureDefinition(
            feature_id=FeatureId("returns_1"),
            name="Returns 1",
            feature_type=FeatureType.MOMENTUM,
            value_type=FeatureValueType.SCALAR,
            parameters={"period": 1},
            lookback=1,
            computation_version="1",
            description="Close-to-close single-period return",
        ),
    ]
    return FeatureSet(
        name="FXTradingFeatureSetV1", version=FeatureSetVersion(1), definitions=definitions
    )


def value_ranges(feature_id: str) -> tuple[float, float] | None:
    """Return the expected [min, max] range for a feature, if known."""
    ranges = {
        "rsi_14": (0.0, 100.0),
        "stochastic_14": (0.0, 100.0),
        "bollinger_20_2": (-1.0, 2.0),
        "returns_1": (-1.0, 1.0),
    }
    return ranges.get(feature_id)
