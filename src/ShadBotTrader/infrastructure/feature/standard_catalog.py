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

    # ── 14) Price Filter — نویززدایی causal ──────────────────────────────
    # Kalman
    definitions += [
        _definition("kalman_price",    "Kalman Filtered Price",         FeatureType.PRICE,       {"kind": "kalman",           "Q": 1e-3, "R": 1e-2},  1,  "price_filter", description="قیمت فیلترشده با Kalman — نویز کمتر، causal"),
        _definition("kalman_gain",     "Kalman Gain",                   FeatureType.STATISTICAL,  {"kind": "kalman_gain",      "Q": 1e-3, "R": 1e-2},  1,  "price_filter", description="Kalman Gain — نزدیک 1=نویز بالا، نزدیک 0=روند پایدار"),
        _definition("kalman_residual", "Kalman Residual (Innovation)",  FeatureType.STATISTICAL,  {"kind": "kalman_residual",  "Q": 1e-3, "R": 1e-2},  1,  "price_filter", description="خطای نوآوری Kalman — قیمت منهای تخمین"),
        _definition("kalman_distance", "Price vs Kalman (relative)",    FeatureType.MOMENTUM,     {"kind": "kalman_distance",  "Q": 1e-3, "R": 1e-2},  1,  "price_filter", description="فاصله نسبی قیمت از Kalman — مثبت=بالاتر از روند"),
    ]
    # Savitzky-Golay causal
    definitions += [
        _definition("sg_smooth",   "Causal SG Smoothed Price",  FeatureType.PRICE,     {"kind": "sg_smooth",   "window": 11, "polyorder": 2}, 10, "price_filter", description="قیمت صاف‌شده با Savitzky-Golay پنجره گذشته"),
        _definition("sg_slope",    "Causal SG Price Slope",     FeatureType.TREND,     {"kind": "sg_slope",    "window": 11, "polyorder": 2}, 10, "price_filter", description="شیب روند از SG — مثبت=صعود، منفی=نزول"),
        _definition("sg_distance", "Price vs SG (relative)",    FeatureType.MOMENTUM,  {"kind": "sg_distance", "window": 11, "polyorder": 2}, 10, "price_filter", description="فاصله نسبی قیمت از خط SG"),
    ]
    # EMA پیشرفته
    definitions += [
        _definition("dema_14",      "DEMA 14",                FeatureType.TREND,    {"kind": "dema",          "period": 14}, 14, "price_filter", description="Double EMA — lag کمتر از EMA معمولی"),
        _definition("tema_14",      "TEMA 14",                FeatureType.TREND,    {"kind": "tema",          "period": 14}, 28, "price_filter", description="Triple EMA — lag خیلی کم"),
        _definition("zlema_14",     "Zero-Lag EMA 14",        FeatureType.TREND,    {"kind": "zlema",         "period": 14}, 14, "price_filter", description="Zero-Lag EMA — بدون تأخیر"),
        _definition("dema_distance","Price vs DEMA (relative)",FeatureType.MOMENTUM, {"kind": "dema_distance", "period": 14}, 14, "price_filter", description="فاصله نسبی قیمت از DEMA"),
    ]

    # ── 15) Volume Analysis ───────────────────────────────────────────────
    definitions += [
        _definition("obv",           "On-Balance Volume",      FeatureType.VOLUME,       {"kind": "obv"},                       1,  "volume_analysis", description="تجمیع حجم بر اساس جهت قیمت"),
        _definition("obv_slope",     "OBV Slope (14)",         FeatureType.VOLUME,       {"kind": "obv_slope",  "period": 14},  15, "volume_analysis", description="شیب OBV — جریان حجم تازه"),
        _definition("mfi_14",        "Money Flow Index 14",    FeatureType.MOMENTUM,     {"kind": "mfi",        "period": 14},  15, "volume_analysis", description="RSI حجم‌دار (0-100)"),
        _definition("cmf_14",        "Chaikin Money Flow 14",  FeatureType.VOLUME,       {"kind": "cmf",        "period": 14},  14, "volume_analysis", description="فشار خرید/فروش حجمی (-1 تا +1)"),
        _definition("cci_14",        "CCI 14",                 FeatureType.MOMENTUM,     {"kind": "cci",        "period": 14},  14, "volume_analysis", description="Commodity Channel Index"),
        _definition("williams_r_14", "Williams %R 14",         FeatureType.MOMENTUM,     {"kind": "williams_r", "period": 14},  14, "volume_analysis", description="Williams %%R (-100 تا 0)"),
        _definition("force_index",   "Force Index",            FeatureType.VOLUME,       {"kind": "force_index"},               1,  "volume_analysis", description="Elder Force Index = Δclose × volume"),
        _definition("volume_roc_14", "Volume ROC 14",          FeatureType.VOLUME,       {"kind": "volume_roc", "period": 14},  14, "volume_analysis", description="نرخ تغییر حجم"),
        _definition("volume_zscore", "Volume Z-Score 20",      FeatureType.STATISTICAL,  {"kind": "volume_zscore","period":20}, 20, "volume_analysis", description="Z-Score حجم در پنجره 20"),
        _definition("volume_ratio",  "Volume Ratio (short/long)", FeatureType.VOLUME,    {"kind": "volume_ratio","period":14},  42, "volume_analysis", description="نسبت میانگین حجم کوتاه به بلندمدت"),
    ]

    # ── 16) Advanced Momentum Oscillators ────────────────────────────────
    definitions += [
        _definition("stoch_rsi_14",   "Stochastic RSI 14",     FeatureType.MOMENTUM,  {"kind": "stoch_rsi",    "period": 14},              28, "momentum_advanced", description="Stochastic روی RSI — حساس‌تر از RSI معمولی"),
        _definition("macd_hist",      "MACD Histogram",        FeatureType.MOMENTUM,  {"kind": "macd_hist",    "fast":12,"slow":26,"signal":9}, 34, "momentum_advanced", description="هیستوگرام MACD — شتاب تغییر"),
        _definition("macd_signal",    "MACD Signal Line",      FeatureType.MOMENTUM,  {"kind": "macd_signal",  "fast":12,"slow":26,"signal":9}, 34, "momentum_advanced", description="خط سیگنال MACD"),
        _definition("roc_14",         "Rate of Change 14",     FeatureType.MOMENTUM,  {"kind": "roc",          "period": 14},              14, "momentum_advanced", description="بازده درصدی 14 کندل"),
        _definition("momentum_14",    "Momentum 14",           FeatureType.MOMENTUM,  {"kind": "momentum",     "period": 14},              14, "momentum_advanced", description="مومنتوم خام: close[t] - close[t-14]"),
        _definition("tsi",            "True Strength Index",   FeatureType.MOMENTUM,  {"kind": "tsi",          "fast": 25, "slow": 13},    38, "momentum_advanced", description="TSI — دو بار smooth‌شده، نویز کم"),
        _definition("awesome_osc",    "Awesome Oscillator",    FeatureType.MOMENTUM,  {"kind": "awesome_osc",  "ao_fast":5,"ao_slow":34},  34, "momentum_advanced", description="Awesome Oscillator = SMA5 - SMA34 از midpoint"),
        _definition("vortex_diff",    "Vortex Diff (+VM - -VM)", FeatureType.TREND,   {"kind": "vortex_diff",  "period": 14},              14, "momentum_advanced", description="تفاضل Vortex: جهت و قوت حرکت"),
    ]

    # ── 17) Session & Time ────────────────────────────────────────────────
    definitions += [
        _definition("session_asian",   "Asian Session",      FeatureType.TIME, {"kind": "session_asian"},   0, "session_time", description="1 = Asian session (00-08 UTC)"),
        _definition("session_london",  "London Session",     FeatureType.TIME, {"kind": "session_london"},  0, "session_time", description="1 = London session (08-16 UTC)"),
        _definition("session_ny",      "NY Session",         FeatureType.TIME, {"kind": "session_ny"},      0, "session_time", description="1 = NY session (13-21 UTC)"),
        _definition("session_overlap", "London-NY Overlap",  FeatureType.TIME, {"kind": "session_overlap"}, 0, "session_time", description="1 = overlap لندن-NY (13-16 UTC) — پرنوسان‌ترین"),
        _definition("hour_sin",        "Hour Sin",           FeatureType.TIME, {"kind": "hour_sin"},        0, "session_time", description="sin ساعت UTC — فرم چرخه‌ای برای ML"),
        _definition("hour_cos",        "Hour Cos",           FeatureType.TIME, {"kind": "hour_cos"},        0, "session_time", description="cos ساعت UTC"),
        _definition("day_sin",         "Day Sin",            FeatureType.TIME, {"kind": "day_sin"},         0, "session_time", description="sin روز هفته — فرم چرخه‌ای"),
        _definition("day_cos",         "Day Cos",            FeatureType.TIME, {"kind": "day_cos"},         0, "session_time", description="cos روز هفته"),
        _definition("is_monday",       "Is Monday",          FeatureType.TIME, {"kind": "is_monday"},       0, "session_time", description="1 = دوشنبه (شروع هفته)"),
        _definition("is_friday",       "Is Friday",          FeatureType.TIME, {"kind": "is_friday"},       0, "session_time", description="1 = جمعه (پایان هفته)"),
    ]

    # ── 18) Adaptive Filters (Ehlers + Kaufman + Chande) ─────────────────
    definitions += [
        _definition("kama_14",             "KAMA 14",                        FeatureType.TREND,       {"kind": "kama",             "period": 14, "fast": 2, "slow": 30}, 14, "adaptive_filters", description="Kaufman Adaptive MA — در روند سریع، در رنج کند"),
        _definition("kama_distance",       "Price vs KAMA",                  FeatureType.MOMENTUM,    {"kind": "kama_distance",    "period": 14},                        14, "adaptive_filters", description="فاصله نسبی قیمت از KAMA"),
        _definition("supersmoother_10",    "Ehlers SuperSmoother (10)",       FeatureType.TREND,       {"kind": "supersmoother",    "period": 10},                        10, "adaptive_filters", description="Ehlers 2-pole IIR — بهترین جایگزین MA"),
        _definition("ss_distance",         "Price vs SuperSmoother",          FeatureType.MOMENTUM,    {"kind": "ss_distance",      "period": 10},                        10, "adaptive_filters", description="فاصله نسبی قیمت از SuperSmoother"),
        _definition("gaussian2_14",        "Gaussian Filter 2-pole (14)",     FeatureType.TREND,       {"kind": "gaussian2",        "period": 14, "poles": 2},            14, "adaptive_filters", description="Ehlers Gaussian 2-pole — نویز کم"),
        _definition("gaussian3_14",        "Gaussian Filter 3-pole (14)",     FeatureType.TREND,       {"kind": "gaussian3",        "period": 14, "poles": 3},            14, "adaptive_filters", description="Ehlers Gaussian 3-pole — نویز خیلی کم"),
        _definition("frama_16",            "FRAMA 16",                        FeatureType.TREND,       {"kind": "frama",            "period": 16},                        16, "adaptive_filters", description="Fractal Adaptive MA — بر اساس بُعد فراکتال"),
        _definition("frama_distance",      "Price vs FRAMA",                  FeatureType.MOMENTUM,    {"kind": "frama_distance",   "period": 16},                        16, "adaptive_filters", description="فاصله نسبی قیمت از FRAMA"),
        _definition("hull_ma_14",          "Hull MA (14)",                    FeatureType.TREND,       {"kind": "hull_ma",          "period": 14},                        14, "adaptive_filters", description="Hull MA — سریع‌ترین MA با نویز کم"),
        _definition("hull_distance",       "Price vs Hull MA",                FeatureType.MOMENTUM,    {"kind": "hull_distance",    "period": 14},                        14, "adaptive_filters", description="فاصله نسبی قیمت از Hull MA"),
        _definition("mcginley_14",         "McGinley Dynamic (14)",           FeatureType.TREND,       {"kind": "mcginley",         "period": 14},                        1,  "adaptive_filters", description="McGinley Dynamic — خودکار سرعت تنظیم می‌کنه"),
        _definition("vidya_14",            "VIDYA (14)",                      FeatureType.TREND,       {"kind": "vidya",            "period": 14},                        14, "adaptive_filters", description="Chande Variable Index Dynamic Average"),
        _definition("vidya_distance",      "Price vs VIDYA",                  FeatureType.MOMENTUM,    {"kind": "vidya_distance",   "period": 14},                        14, "adaptive_filters", description="فاصله نسبی قیمت از VIDYA"),
        _definition("laguerre_filter",     "Ehlers Laguerre Filter",          FeatureType.TREND,       {"kind": "laguerre",         "gamma": 0.8},                        4,  "adaptive_filters", description="Ehlers 4-tap Laguerre — lag خیلی کم"),
        _definition("laguerre_distance",   "Price vs Laguerre",               FeatureType.MOMENTUM,    {"kind": "laguerre_distance","gamma": 0.8},                        4,  "adaptive_filters", description="فاصله نسبی قیمت از Laguerre"),
    ]

    # ── 19) Ehlers DSP / Cycle features ───────────────────────────────────
    definitions += [
        _definition("roofing_filter",      "Roofing Filter (Ehlers)",         FeatureType.TREND,       {"kind": "roofing_filter",    "period": 10, "hp_period": 48},  58, "ehlers_cycle", description="HP + SS: فقط سیکل‌های بازار — ترند و نویز حذف"),
        _definition("cyber_cycle",         "Cyber Cycle (Ehlers)",            FeatureType.MOMENTUM,    {"kind": "cyber_cycle",       "period": 10, "hp_period": 48},  58, "ehlers_cycle", description="فاز سیکل بازار — اشباع خرید/فروش"),
        _definition("fisher_transform",    "Fisher Transform",                FeatureType.MOMENTUM,    {"kind": "fisher_transform",  "period": 10},                    10, "ehlers_cycle", description="قیمت در توزیع Gaussian — نقاط اشباع واضح"),
        _definition("inverse_fisher_rsi",  "Inverse Fisher RSI",              FeatureType.MOMENTUM,    {"kind": "inverse_fisher",    "rsi_period": 14},                15, "ehlers_cycle", description="RSI در توزیع Gaussian — بهتر از RSI معمولی"),
        _definition("center_of_gravity",   "Center of Gravity (Ehlers)",      FeatureType.MOMENTUM,    {"kind": "center_of_gravity", "cog_period": 10},                10, "ehlers_cycle", description="مرکز ثقل قیمت — پیش‌بینی نقاط بازگشت"),
        _definition("laguerre_rsi",        "Laguerre RSI (Ehlers)",           FeatureType.MOMENTUM,    {"kind": "laguerre_rsi",      "gamma": 0.5},                    4,  "ehlers_cycle", description="RSI با Laguerre — lag خیلی کمتر"),
        _definition("cybernetic_osc",      "Cybernetic Oscillator (2025)",    FeatureType.MOMENTUM,    {"kind": "cybernetic_osc",    "period": 20, "hp_period": 30, "rms_period": 50}, 80, "ehlers_cycle", description="جدیدترین اوسیلاتور Ehlers (TASC 2025) — نرمال‌شده"),
    ]

    # ── 20) Fractal & Statistical features ───────────────────────────────
    definitions += [
        _definition("hurst_20",            "Hurst Exponent (20)",             FeatureType.STATISTICAL,  {"kind": "hurst",              "period": 20},  20, "fractal_stats", description="H<0.5 = mean-rev | H=0.5 = رندوم | H>0.5 = trending"),
        _definition("fractal_dim_20",      "Fractal Dimension (20)",          FeatureType.STATISTICAL,  {"kind": "fractal_dimension",  "period": 20},  20, "fractal_stats", description="بُعد فراکتال سری قیمت = 2 - Hurst"),
        _definition("rolling_skew",        "Rolling Skewness (20)",           FeatureType.STATISTICAL,  {"kind": "rolling_skew",       "period": 20},  20, "fractal_stats", description="چولگی بازده — ریسک دنباله"),
        _definition("rolling_kurt",        "Rolling Kurtosis (20)",           FeatureType.STATISTICAL,  {"kind": "rolling_kurt",       "period": 20},  20, "fractal_stats", description="کشیدگی بازده — دم‌پهنی توزیع"),
        _definition("rolling_entropy",     "Shannon Entropy (20)",            FeatureType.STATISTICAL,  {"kind": "rolling_entropy",    "period": 20},  20, "fractal_stats", description="بی‌نظمی سری — بالا = رندوم‌تر"),
        _definition("autocorr_lag1",       "Autocorrelation Lag-1",           FeatureType.STATISTICAL,  {"kind": "autocorr_lag1",      "period": 20},  21, "fractal_stats", description="همبستگی lag-1 بازده — حافظه کوتاه"),
        _definition("autocorr_lag5",       "Autocorrelation Lag-5",           FeatureType.STATISTICAL,  {"kind": "autocorr_lag5",      "period": 20},  25, "fractal_stats", description="همبستگی lag-5 بازده — الگوی هفتگی"),
        _definition("parkinson_vol",       "Parkinson Volatility (20)",       FeatureType.VOLATILITY,   {"kind": "parkinson_vol",      "period": 20},  20, "fractal_stats", description="Parkinson (1980): σ از High-Low — دقیق‌تر از close-to-close"),
        _definition("garman_klass_vol",    "Garman-Klass Volatility (20)",    FeatureType.VOLATILITY,   {"kind": "garman_klass_vol",   "period": 20},  20, "fractal_stats", description="Garman-Klass (1980): σ از OHLC"),
        _definition("yang_zhang_vol",      "Yang-Zhang Volatility (20)",      FeatureType.VOLATILITY,   {"kind": "yang_zhang_vol",     "period": 20},  21, "fractal_stats", description="Yang-Zhang (2000): بهترین تخمین σ از OHLC + overnight"),
        _definition("vol_of_vol",          "Volatility of Volatility (20)",   FeatureType.VOLATILITY,   {"kind": "vol_of_vol",         "period": 20},  40, "fractal_stats", description="نوسان ATR — ناپایداری بازار"),
    ]

    # ── 21) Volatility Breakout (Squeeze) ─────────────────────────────────
    definitions += [
        _definition(
            feature_id="atr_ratio",
            name="ATR Ratio (fast/slow)",
            feature_type=FeatureType.VOLATILITY,
            parameters={"kind": "atr_ratio", "atr_fast": 5, "atr_slow": 20},
            lookback=21,
            family="volatility_breakout",
            description="نسبت ATR(5) به ATR(20) — بالا = افزایش volatility",
        ),
        _definition(
            feature_id="bb_squeeze",
            name="Bollinger Squeeze",
            feature_type=FeatureType.VOLATILITY,
            parameters={"kind": "bb_squeeze", "bb_period": 20, "bb_std": 2.0, "kc_period": 20, "kc_mult": 1.5},
            lookback=21,
            family="volatility_breakout",
            description="1 = squeeze فعال (BB داخل Keltner)، 0 = بدون squeeze",
        ),
        _definition(
            feature_id="bb_width",
            name="Bollinger Band Width",
            feature_type=FeatureType.VOLATILITY,
            parameters={"kind": "bb_width", "bb_period": 20, "bb_std": 2.0, "kc_period": 20, "kc_mult": 1.5},
            lookback=20,
            family="volatility_breakout",
            description="عرض نسبی باند Bollinger به قیمت",
        ),
        _definition(
            feature_id="keltner_width",
            name="Keltner Channel Width",
            feature_type=FeatureType.VOLATILITY,
            parameters={"kind": "keltner_width", "bb_period": 20, "bb_std": 2.0, "kc_period": 20, "kc_mult": 1.5},
            lookback=21,
            family="volatility_breakout",
            description="عرض نسبی کانال Keltner به قیمت",
        ),
        _definition(
            feature_id="squeeze_intensity",
            name="Squeeze Intensity",
            feature_type=FeatureType.VOLATILITY,
            parameters={"kind": "squeeze_intensity", "bb_period": 20, "bb_std": 2.0, "kc_period": 20, "kc_mult": 1.5},
            lookback=21,
            family="volatility_breakout",
            description="شدت فشردگی: منفی = squeeze قوی، مثبت = انبساط",
        ),
    ]

    # ── 15) Trend Strength (ADX / EMA) ────────────────────────────────────
    definitions += [
        _definition(
            feature_id="adx_14",
            name="ADX 14",
            feature_type=FeatureType.TREND,
            parameters={"kind": "adx", "period": 14},
            lookback=28,
            family="trend_strength",
            description="شاخص قوت روند ADX (0-100) — بالای 25 = روند قوی",
        ),
        _definition(
            feature_id="plus_di_14",
            name="+DI 14",
            feature_type=FeatureType.TREND,
            parameters={"kind": "plus_di", "period": 14},
            lookback=28,
            family="trend_strength",
            description="قوت روند صعودی (+DI)",
        ),
        _definition(
            feature_id="minus_di_14",
            name="-DI 14",
            feature_type=FeatureType.TREND,
            parameters={"kind": "minus_di", "period": 14},
            lookback=28,
            family="trend_strength",
            description="قوت روند نزولی (-DI)",
        ),
        _definition(
            feature_id="di_spread",
            name="DI Spread (+DI - -DI)",
            feature_type=FeatureType.TREND,
            parameters={"kind": "di_spread", "period": 14},
            lookback=28,
            family="trend_strength",
            description="جهت روند: +DI منهای -DI (مثبت = صعودی)",
        ),
        _definition(
            feature_id="ema_cross_10_30",
            name="EMA Cross (10/30)",
            feature_type=FeatureType.TREND,
            parameters={"kind": "ema_cross", "fast": 10, "slow": 30},
            lookback=30,
            family="trend_strength",
            description="نسبت EMA(10) به EMA(30) — بالای 1 = صعودی",
        ),
        _definition(
            feature_id="price_vs_ema30",
            name="Price vs EMA30",
            feature_type=FeatureType.TREND,
            parameters={"kind": "price_vs_ema", "slow": 30},
            lookback=30,
            family="trend_strength",
            description="فاصله نسبی قیمت از EMA(30)",
        ),
    ]

    # ── 16) Mean Reversion ────────────────────────────────────────────────
    definitions += [
        _definition(
            feature_id="zscore_20",
            name="Z-Score (20)",
            feature_type=FeatureType.STATISTICAL,
            parameters={"kind": "zscore", "period": 20},
            lookback=20,
            family="mean_reversion",
            description="Z-Score قیمت در پنجره 20 کندلی",
        ),
        _definition(
            feature_id="rsi_distance",
            name="RSI Distance from 50",
            feature_type=FeatureType.MOMENTUM,
            parameters={"kind": "rsi_distance", "period": 14},
            lookback=14,
            family="mean_reversion",
            description="فاصله RSI از 50 — مثبت = اشباع خرید، منفی = اشباع فروش",
        ),
        _definition(
            feature_id="close_vs_vwap",
            name="Close vs VWAP",
            feature_type=FeatureType.PRICE,
            parameters={"kind": "close_vs_vwap", "period": 20},
            lookback=20,
            family="mean_reversion",
            description="فاصله نسبی قیمت پایانی از VWAP rolling",
        ),
        _definition(
            feature_id="momentum_ratio_5_20",
            name="Momentum Ratio (5/20)",
            feature_type=FeatureType.MOMENTUM,
            parameters={"kind": "momentum_ratio", "fast": 5, "slow": 20},
            lookback=20,
            family="mean_reversion",
            description="نسبت مومنتوم کوتاه به بلندمدت — پایین‌تر از 1 = احتمال reversal",
        ),
    ]

    # ── 17) Candle Pattern ────────────────────────────────────────────────
    definitions += [
        _definition(
            feature_id="body_ratio",
            name="Candle Body Ratio",
            feature_type=FeatureType.MICROSTRUCTURE,
            parameters={"kind": "body_ratio"},
            lookback=0,
            family="candle_pattern",
            description="نسبت body به کل کندل (0 تا 1) — نزدیک 1 = کندل قوی",
        ),
        _definition(
            feature_id="upper_wick_ratio",
            name="Upper Wick Ratio",
            feature_type=FeatureType.MICROSTRUCTURE,
            parameters={"kind": "upper_wick_ratio"},
            lookback=0,
            family="candle_pattern",
            description="نسبت سایه بالایی به کل کندل — بالا = فشار فروش",
        ),
        _definition(
            feature_id="lower_wick_ratio",
            name="Lower Wick Ratio",
            feature_type=FeatureType.MICROSTRUCTURE,
            parameters={"kind": "lower_wick_ratio"},
            lookback=0,
            family="candle_pattern",
            description="نسبت سایه پایینی به کل کندل — بالا = فشار خرید",
        ),
        _definition(
            feature_id="engulfing",
            name="Engulfing Pattern",
            feature_type=FeatureType.MICROSTRUCTURE,
            parameters={"kind": "engulfing"},
            lookback=1,
            family="candle_pattern",
            description="+1 = پوشش صعودی، -1 = پوشش نزولی، 0 = خنثی",
        ),
        _definition(
            feature_id="inside_bar",
            name="Inside Bar",
            feature_type=FeatureType.MICROSTRUCTURE,
            parameters={"kind": "inside_bar"},
            lookback=1,
            family="candle_pattern",
            description="1 = کندل داخل کندل قبلی (نشانه فشردگی)",
        ),
        _definition(
            feature_id="high_low_range",
            name="High-Low Range / ATR",
            feature_type=FeatureType.VOLATILITY,
            parameters={"kind": "high_low_range", "period": 14},
            lookback=14,
            family="candle_pattern",
            description="اندازه نسبی کندل نسبت به ATR(14)",
        ),
    ]

    # ── 18) Market Regime ─────────────────────────────────────────────────
    definitions += [
        _definition(
            feature_id="efficiency_ratio",
            name="Efficiency Ratio (Kaufman)",
            feature_type=FeatureType.TREND,
            parameters={"kind": "efficiency_ratio", "period": 14},
            lookback=14,
            family="market_regime",
            description="نسبت کارایی Kaufman (0 = رندوم، 1 = روند خالص)",
        ),
        _definition(
            feature_id="vol_regime",
            name="Volatility Regime",
            feature_type=FeatureType.VOLATILITY,
            parameters={"kind": "vol_regime", "period": 14, "long_period": 50},
            lookback=51,
            family="market_regime",
            description="نسبت ATR کوتاه به بلند — بالای 1 = volatility در حال افزایش",
        ),
        _definition(
            feature_id="choppiness_14",
            name="Choppiness Index (14)",
            feature_type=FeatureType.STATISTICAL,
            parameters={"kind": "choppiness", "period": 14},
            lookback=14,
            family="market_regime",
            description="شاخص choppy (100=ranging، 0=trending خالص)",
        ),
        _definition(
            feature_id="trend_score",
            name="Trend Score",
            feature_type=FeatureType.TREND,
            parameters={"kind": "trend_score", "period": 14},
            lookback=42,
            family="market_regime",
            description="امتیاز ترکیبی روند: EMA slope × Efficiency Ratio",
        ),
    ]

    # ── 22) Ehlers Advanced (Cycle Analytics + Cybernetic Analysis) ──────
    definitions += [
        _definition("reflex_20",       "ReFlex (20)",              FeatureType.MOMENTUM,    {"kind": "reflex",        "period": 20},                    23, "ehlers_advanced", description="ReFlex: انحراف قیمت از روند پیش‌بینی‌شده (Cycle Analytics 2013)"),
        _definition("trendflex_20",    "TrendFlex (20)",           FeatureType.TREND,       {"kind": "trendflex",     "period": 20},                    23, "ehlers_advanced", description="TrendFlex: قوت روند نرمال‌شده (Cycle Analytics 2013)"),
        _definition("ebsw",            "Even Better Sinewave",     FeatureType.MOMENTUM,    {"kind": "ebsw",          "period": 10, "hp_period": 36},   46, "ehlers_advanced", description="EBSW: بازار cyclic یا trending؟ (Cycle Analytics 2013)"),
        _definition("rvi",             "Relative Vigor Index",     FeatureType.MOMENTUM,    {"kind": "rvi"},                                            10, "ehlers_advanced", description="RVI: قدرت نسبی close vs open (Cybernetic Analysis 2004)"),
        _definition("rvi_signal",      "RVI Signal",               FeatureType.MOMENTUM,    {"kind": "rvi_signal"},                                     10, "ehlers_advanced", description="RVI Signal: خط سیگنال RVI"),
        _definition("decycler",        "Decycler",                 FeatureType.TREND,       {"kind": "decycler",      "hp_period": 40},                 40, "ehlers_advanced", description="Decycler: ترند خالص بدون سیکل (Cycle Analytics 2013)"),
        _definition("decycler_osc",    "Decycler Oscillator",      FeatureType.MOMENTUM,    {"kind": "decycler_osc",  "fast_hp": 10, "slow_hp": 20},    20, "ehlers_advanced", description="Decycler Osc: تفاضل دو Decycler — جهت و قوت"),
    ]

    # ── 23) Lopez de Prado Features ───────────────────────────────────────
    definitions += [
        _definition("frac_diff_04",    "Frac. Diff. (d=0.4)",      FeatureType.STATISTICAL, {"kind": "frac_diff",       "d": 0.4, "threshold": 1e-2},  11, "prado_features", description="Fractional Diff d=0.4: stationary + حافظه (Lopez de Prado Ch.5)"),
        _definition("frac_diff_ret",   "Frac. Diff. Returns",      FeatureType.MOMENTUM,    {"kind": "frac_diff_ret",   "d": 0.3, "threshold": 1e-2},   8, "prado_features", description="Fractional Diff روی log-returns (d=0.3)"),
        _definition("cusum_pos",       "CUSUM Positive",           FeatureType.MOMENTUM,    {"kind": "cusum_pos"},                     1, "prado_features", description="CUSUM مثبت: انباشت حرکت صعودی (Lopez de Prado)"),
        _definition("cusum_neg",       "CUSUM Negative",           FeatureType.MOMENTUM,    {"kind": "cusum_neg"},                     1, "prado_features", description="CUSUM منفی: انباشت حرکت نزولی"),
        _definition("rolling_sharpe",  "Rolling Sharpe (20)",      FeatureType.STATISTICAL, {"kind": "rolling_sharpe",  "period": 20}, 20, "prado_features", description="Sharpe ratio rolling: کیفیت بازده"),
        _definition("rolling_calmar",  "Rolling Calmar (20)",      FeatureType.STATISTICAL, {"kind": "rolling_calmar",  "period": 20}, 20, "prado_features", description="Calmar ratio rolling: return/drawdown"),
        _definition("kyles_lambda",    "Kyle's Lambda",            FeatureType.STATISTICAL, {"kind": "kyles_lambda",    "period": 20}, 21, "prado_features", description="Kyle's Lambda: market impact — بازار کم‌عمق = بالا"),
        _definition("amihud_illiq",    "Amihud Illiquidity",       FeatureType.STATISTICAL, {"kind": "amihud_illiq",    "period": 20}, 21, "prado_features", description="Amihud (2002): |r|/volume — نقدشوندگی"),
        _definition("bid_ask_spread",  "Bid-Ask Spread (Roll)",    FeatureType.STATISTICAL, {"kind": "bid_ask_spread",  "period": 20}, 22, "prado_features", description="Roll (1984): تخمین spread از serial covariance"),
    ]

    # ── 24) Market Structure Features ────────────────────────────────────
    definitions += [
        _definition("donchian_pos",    "Donchian Position (20)",   FeatureType.PRICE,       {"kind": "donchian_pos",    "period": 20}, 20, "structure_features", description="موقعیت قیمت در کانال Donchian (0 تا 1)"),
        _definition("donchian_width",  "Donchian Width (20)",      FeatureType.VOLATILITY,  {"kind": "donchian_width",  "period": 20}, 20, "structure_features", description="عرض نسبی کانال Donchian"),
        _definition("donchian_mid",    "Donchian Mid (20)",        FeatureType.TREND,       {"kind": "donchian_mid",    "period": 20}, 20, "structure_features", description="میانه کانال Donchian"),
        _definition("linreg_slope",    "LinReg Slope (20)",        FeatureType.TREND,       {"kind": "linreg_slope",    "period": 20}, 20, "structure_features", description="شیب رگرسیون خطی نرمال‌شده — جهت روند"),
        _definition("linreg_r2",       "LinReg R² (20)",           FeatureType.STATISTICAL, {"kind": "linreg_r2",       "period": 20}, 20, "structure_features", description="R² رگرسیون — چقدر قیمت از خط خطی پیروی می‌کنه"),
        _definition("linreg_deviation","LinReg Deviation (20)",    FeatureType.MOMENTUM,    {"kind": "linreg_deviation","period": 20}, 20, "structure_features", description="انحراف قیمت از خط رگرسیون — نقاط برگشت"),
        _definition("gap_up",          "Gap Up",                   FeatureType.PRICE,       {"kind": "gap_up"},                         1, "structure_features", description="شکاف صعودی: open > prev_high (0/1)"),
        _definition("gap_down",        "Gap Down",                 FeatureType.PRICE,       {"kind": "gap_down"},                       1, "structure_features", description="شکاف نزولی: open < prev_low (0/1)"),
        _definition("gap_size",        "Gap Size",                 FeatureType.PRICE,       {"kind": "gap_size"},                       1, "structure_features", description="اندازه نسبی شکاف قیمت"),
        _definition("close_location",  "Close Location (CL)",      FeatureType.PRICE,       {"kind": "close_location"},                 0, "structure_features", description="موقعیت close در کندل: 0=پایین، 1=بالا"),
        _definition("chandelier_dist", "Chandelier Distance",      FeatureType.VOLATILITY,  {"kind": "chandelier_dist", "period": 22, "atr_mult": 3.0}, 22, "structure_features", description="فاصله نسبی قیمت از Chandelier Exit (3×ATR)"),
    ]

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
