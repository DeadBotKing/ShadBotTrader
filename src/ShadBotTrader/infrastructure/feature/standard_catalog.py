"""The standard FX feature catalog (full set, ported from the legacy system).

Every feature family that existed in the legacy ``FeatureEngineering``
dataset is reproduced here as clean, causal (or explicitly non-causal),
parameterised definitions. Raw OHLC and derived price columns
(``HL/2``, ``HLC/3``, ``HLCC/4``, ``OHLC/4``) are supplied by the Data
Platform candles; everything below is computed by the Feature Platform.
"""

from __future__ import annotations

from typing import List

from ShadBotTrader.domain.feature.feature_definition import (
    FeatureDefinition,
    FeatureId,
)
from ShadBotTrader.domain.feature.feature_set import FeatureSet, FeatureSetVersion
from ShadBotTrader.domain.feature.feature_types import (
    Causality,
    FeatureType,
    FeatureValueType,
)

PRICE_COLUMNS = ("open", "close", "low", "high", "HL/2", "HLC/3", "HLCC/4", "OHLC/4")
_SMA_PERIODS = (5, 10, 15, 20, 25, 30, 35)
_EMA_PERIODS = (5, 10, 15, 20, 25, 30, 35)
_ATR_PERIODS = (5, 10, 15, 20, 25, 30, 35)


def _definition(
    feature_id: str,
    name: str,
    feature_type: FeatureType,
    parameters: dict,
    lookback: int,
    family: str,
    causality: Causality = Causality.CAUSAL,
    description: str = "",
    forward_lookahead: int = 0,
    leakage_reason: str = "",
) -> FeatureDefinition:
    return FeatureDefinition(
        feature_id=FeatureId(feature_id),
        name=name,
        feature_type=feature_type,
        value_type=FeatureValueType.SCALAR,
        parameters=parameters,
        lookback=lookback,
        computation_version="1",
        causality=causality,
        description=description,
        family=family,
        forward_lookahead=forward_lookahead,
        leakage_reason=leakage_reason,
    )


def _slug(column: str) -> str:
    """Turn a legacy price column into a snake-case feature-id fragment."""
    return column.replace("/", "").replace(" ", "_").lower()


def _build_definitions() -> List[FeatureDefinition]:
    definitions: List[FeatureDefinition] = []

    # 1) Wavelet noise-filtered prices (legacy: *_filter columns)
    for column in PRICE_COLUMNS:
        definitions.append(
            _definition(
                feature_id=f"{_slug(column)}_filter",
                name=f"{column} (noise filtered)",
                feature_type=FeatureType.DERIVED,
                parameters={"column": column},
                lookback=0,
                family="noise_filter",
                causality=Causality.NON_CAUSAL,
                leakage_reason="FULL_SERIES_WAVELET",
                description="Wavelet (haar/db6/dmey) denoised price; research only",
            )
        )

    # 2) SMA (legacy: sma_5 .. sma_35)
    for period in _SMA_PERIODS:
        definitions.append(
            _definition(
                feature_id=f"sma_{period}",
                name=f"SMA {period}",
                feature_type=FeatureType.TREND,
                parameters={"period": period, "column": "close"},
                lookback=period - 1,
                family="sma",
                description=f"Simple moving average over {period} candles",
            )
        )

    # 3) EMA (legacy: ema_5 .. ema_35)
    for period in _EMA_PERIODS:
        definitions.append(
            _definition(
                feature_id=f"ema_{period}",
                name=f"EMA {period}",
                feature_type=FeatureType.TREND,
                parameters={"period": period, "column": "close"},
                lookback=period - 1,
                family="ema",
                description=f"Exponential moving average over {period} candles",
            )
        )

    # 4) ATR — Wilder (atr_14) + raw true range (legacy atr_tr_5..35)
    definitions.append(
        _definition(
            feature_id="atr_14",
            name="ATR 14",
            feature_type=FeatureType.VOLATILITY,
            parameters={"period": 14, "mode": "rma"},
            lookback=14,
            family="atr",
            description="Wilder average true range over 14 candles",
        )
    )
    for period in _ATR_PERIODS:
        definitions.append(
            _definition(
                feature_id=f"atr_tr_{period}",
                name=f"ATR TR {period}",
                feature_type=FeatureType.VOLATILITY,
                parameters={"period": period, "mode": "tr"},
                lookback=1,
                family="atr",
                description="True range (legacy atr_tr series)",
            )
        )

    # 5) Bollinger bands (legacy: bband_lower / bband_mid / bband_upper)
    for band in ("lower", "mid", "upper"):
        definitions.append(
            _definition(
                feature_id=f"bband_{band}",
                name=f"Bollinger {band}",
                feature_type=FeatureType.STATISTICAL,
                parameters={"period": 20, "num_std": 2.0, "band": band, "column": "close"},
                lookback=19,
                family="bband",
                description=f"Bollinger {band} band (20, 2)",
            )
        )
    definitions.append(
        _definition(
            feature_id="bollinger_20_2",
            name="Bollinger %B (20, 2)",
            feature_type=FeatureType.STATISTICAL,
            parameters={"period": 20, "num_std": 2.0},
            lookback=19,
            family="bollinger",
            description="Bollinger %B position",
        )
    )

    # 6) Ichimoku (legacy: spana/spanb/tenkan/kijun/chikou)
    for line in ("spana", "spanb", "tenkan", "kijun", "chikou"):
        definitions.append(
            _definition(
                feature_id=line,
                name=f"Ichimoku {line}",
                feature_type=FeatureType.TREND,
                parameters={"line": line, "tenkan": 9, "kijun": 26, "senkou": 52},
                lookback=51,
                family="ichimoku",
                causality=(Causality.NON_CAUSAL if line == "chikou" else Causality.CAUSAL),
                forward_lookahead=26 if line == "chikou" else 0,
                leakage_reason="FUTURE_SHIFT" if line == "chikou" else "",
                description=f"Ichimoku {line} line (9/26/52)",
            )
        )

    # 7) RSI + MACD + Stochastic (legacy oscillator features)
    definitions.append(
        _definition(
            feature_id="rsi_14",
            name="RSI 14",
            feature_type=FeatureType.MOMENTUM,
            parameters={"period": 14},
            lookback=14,
            family="rsi",
            description="Wilder RSI over 14 candles",
        )
    )
    definitions.append(
        _definition(
            feature_id="macd_12_26_9",
            name="MACD 12/26/9",
            feature_type=FeatureType.MOMENTUM,
            parameters={"fast": 12, "slow": 26, "signal": 9},
            lookback=33,
            family="macd",
            description="MACD line (12/26/9)",
        )
    )
    definitions.append(
        _definition(
            feature_id="stochastic_14",
            name="Stochastic %K 14",
            feature_type=FeatureType.MOMENTUM,
            parameters={"period": 14},
            lookback=13,
            family="stochastic",
            description="Stochastic %K over 14 candles",
        )
    )

    # 8) Returns per column (legacy: {col}_return_{tf}_{period})
    for column in list(PRICE_COLUMNS) + ["volume"]:
        definitions.append(
            _definition(
                feature_id=f"{_slug(column)}_return_1",
                name=f"{column} return 1",
                feature_type=FeatureType.MOMENTUM,
                parameters={"column": column, "period": 1},
                lookback=1,
                family="returns",
                description=f"Single-period return of {column}",
            )
        )

    # 9) Target shifts — past (causal) and future (non-causal)
    for column in list(PRICE_COLUMNS) + ["volume"]:
        definitions.append(
            _definition(
                feature_id=f"{_slug(column)}_target_m1",
                name=f"{column} target (-1)",
                feature_type=FeatureType.DERIVED,
                parameters={"column": column, "shift": -1},
                lookback=0,
                family="target",
                description=f"{column} shifted one candle back",
            )
        )
        definitions.append(
            _definition(
                feature_id=f"{_slug(column)}_target_p1",
                name=f"{column} target (+1)",
                feature_type=FeatureType.DERIVED,
                parameters={"column": column, "shift": 1},
                lookback=0,
                family="target",
                causality=Causality.NON_CAUSAL,
                forward_lookahead=1,
                leakage_reason="FUTURE_VALUE",
                description=f"{column} shifted one candle forward (research only)",
            )
        )

    # 10) Fourier resonance (legacy: sin_{tf}_{col} / cos_{tf}_{col})
    for column in PRICE_COLUMNS:
        for function in ("sin", "cos"):
            definitions.append(
                _definition(
                    feature_id=f"{function}_{_slug(column)}",
                    name=f"{function} of {column} cycle",
                    feature_type=FeatureType.DERIVED,
                    parameters={"column": column, "function": function},
                    lookback=0,
                    family="fourier",
                    causality=Causality.NON_CAUSAL,
                    leakage_reason="FULL_SERIES_FOURIER_FIT",
                    description=(
                        f"{function} of the dominant {column} cycle "
                        "(frequency fitted on the full series; research only)"
                    ),
                )
            )

    # 11) Balance / pattern (legacy: color_candle, extension, power)
    definitions.append(
        _definition(
            feature_id="color_candle",
            name="Candle color",
            feature_type=FeatureType.PRICE,
            parameters={"kind": "color"},
            lookback=0,
            family="balance",
            description="1 for bullish candle, 0 for bearish",
        )
    )
    for color in ("green", "red"):
        definitions.append(
            _definition(
                feature_id=f"extension_{color}",
                name=f"Extension {color}",
                feature_type=FeatureType.MICROSTRUCTURE,
                parameters={"kind": "extension", "color": color},
                lookback=0,
                family="balance",
                description=f"Volume/price extension of {color} candles",
            )
        )
        definitions.append(
            _definition(
                feature_id=f"power_{color}",
                name=f"Power {color}",
                feature_type=FeatureType.MICROSTRUCTURE,
                parameters={"kind": "power", "color": color},
                lookback=0,
                family="balance",
                description=f"Body-to-wick power of {color} candles",
            )
        )

    # 12) PCA components (legacy: pca0 .. pca6)
    for component in range(7):
        definitions.append(
            _definition(
                feature_id=f"pca{component}",
                name=f"PCA component {component}",
                feature_type=FeatureType.STATISTICAL,
                parameters={"component": component},
                lookback=0,
                family="pca",
                causality=Causality.NON_CAUSAL,
                leakage_reason="FULL_SERIES_PCA_FIT",
                description=(
                    f"{component}-th principal component of OHLCV " "(batch SVD; research only)"
                ),
            )
        )

    # 13) Divergence (legacy: 12 oscillator divergence features)
    divergence_specs = [
        ("macdh", "buy"),
        ("macdh", "buy"),
        ("macds", "sell"),
        ("macd", "sell"),
        ("stoch_d", "buy"),
        ("stoch_k", "sell"),
        ("stoch_k", "sell"),
        ("stoch_k", "buy"),
        ("rsi", "buy"),
        ("rsi", "sell"),
        ("rsi", "sell"),
        ("rsi", "buy"),
    ]
    divergence_ids = [
        "macdh_buy_primary",
        "macdh_buy_secondry",
        "macds_sell_secondry",
        "macd_sell_primary",
        "stochastic_d_buy_primary",
        "stochastic_k_sell_secondry",
        "stochastic_k_sell_primary",
        "stochastic_k_buy_secondry",
        "rsi_buy_primary",
        "rsi_sell_secondry",
        "rsi_sell_primary",
        "rsi_buy_secondry",
    ]
    for (indicator, signaltype), feature_id in zip(divergence_specs, divergence_ids, strict=False):
        definitions.append(
            _definition(
                feature_id=feature_id,
                name=f"{indicator} divergence {signaltype}",
                feature_type=FeatureType.MODEL_BASED,
                parameters={"indicator": indicator, "signaltype": signaltype},
                lookback=0,
                family="divergence",
                causality=Causality.NON_CAUSAL,
                leakage_reason="CENTERED_FUTURE_EXTREMA",
                description=(
                    f"Classic {signaltype} divergence of {indicator} vs price; research only"
                ),
            )
        )

    return definitions


def standard_feature_set() -> FeatureSet:
    """Return the full standard FX feature set (v1)."""
    return FeatureSet(
        name="FXTradingFeatureSetV1",
        version=FeatureSetVersion(1),
        definitions=_build_definitions(),
    )


def standard_feature_set_v1() -> FeatureSet:
    """Backward-compatible alias of :func:`standard_feature_set`."""
    return standard_feature_set()


def value_ranges(feature_id: str) -> tuple[float, float] | None:
    """Return the expected [min, max] range for a feature, if known."""
    ranges = {
        "rsi_14": (0.0, 100.0),
        "stochastic_14": (0.0, 100.0),
        "bollinger_20_2": (-1.0, 2.0),
    }
    return ranges.get(feature_id)
