"""Enumerations of the AI domain (Phase 13, sections 6-7, 19, 23, 50)."""

from __future__ import annotations

from enum import Enum


class ModelType(str, Enum):
    """The conceptual problem type a model solves (section 6)."""

    REGRESSION = "regression"
    CLASSIFICATION = "classification"
    TIME_SERIES = "time_series"
    SEQUENCE = "sequence"
    ANOMALY_DETECTION = "anomaly_detection"
    CLUSTERING = "clustering"
    RANKING = "ranking"
    REINFORCEMENT = "reinforcement"
    ENSEMBLE = "ensemble"
    HYBRID = "hybrid"


class ModelFamily(str, Enum):
    """The architectural family of a model (section 7)."""

    LINEAR = "linear"
    TREE_BASED = "tree_based"
    NEURAL_NETWORK = "neural_network"
    CNN = "cnn"
    RNN = "rnn"
    LSTM = "lstm"
    GRU = "gru"
    TRANSFORMER = "transformer"
    TCN = "tcn"
    WAVENET = "wavenet"
    ENSEMBLE = "ensemble"


class ModelStatus(str, Enum):
    """Lifecycle status of a model version (section 50)."""

    REGISTERED = "registered"
    IN_TRAINING = "in_training"
    TRAINED = "trained"
    EVALUATED = "evaluated"
    APPROVED = "approved"
    DEPLOYED = "deployed"
    RETIRED = "retired"
    REJECTED = "rejected"


class PredictionType(str, Enum):
    """The kind of value a prediction carries (section 19)."""

    DIRECTION = "direction"
    PRICE = "price"
    PROBABILITY = "probability"
    CLASS_LABEL = "class_label"


class InferenceMode(str, Enum):
    """How inference is executed (section 23)."""

    LIVE = "live"
    BACKTEST = "backtest"
    REPLAY = "replay"
