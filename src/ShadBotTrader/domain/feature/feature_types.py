"""Enumerations of the feature domain (Phase 12, sections 7-8, 28-30)."""

from __future__ import annotations

from enum import Enum


class FeatureType(str, Enum):
    """The semantic category of a feature."""

    PRICE = "price"
    VOLUME = "volume"
    VOLATILITY = "volatility"
    MOMENTUM = "momentum"
    TREND = "trend"
    STATISTICAL = "statistical"
    MICROSTRUCTURE = "microstructure"
    FUNDAMENTAL = "fundamental"
    SENTIMENT = "sentiment"
    TIME = "time"
    CROSS_ASSET = "cross_asset"
    DERIVED = "derived"
    MODEL_BASED = "model_based"


class FeatureValueType(str, Enum):
    """The shape of a feature's output value."""

    SCALAR = "scalar"
    VECTOR = "vector"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    SEQUENCE = "sequence"


class Causality(str, Enum):
    """Whether a feature may use future observations (sections 28-29)."""

    CAUSAL = "causal"
    NON_CAUSAL = "non_causal"


class ExecutionMode(str, Enum):
    """How a feature may be computed (section 30)."""

    BATCH = "batch"
    STREAM = "stream"
    ONLINE = "online"
    INCREMENTAL = "incremental"
    REPLAY = "replay"
