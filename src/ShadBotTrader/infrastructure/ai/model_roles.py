"""The two model roles of Phase 29, with their defaults.

A role binds together everything that makes one of the two models what
it is: the question it answers, the timeframe it reads, how far ahead it
looks, and the shape of its output head. Keeping that in one object
prevents the combination drifting apart across the trainer, the CLI and
the dashboard.

Defaults follow the user requirement: **1H for the range model, 5M for
the signal model**. Hourly bars carry enough structure for a multi-bar
range to mean something, while 5-minute extremes are mostly
microstructure noise; the signal model in turn needs the resolution to
act.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from ShadBotTrader.domain.ai.prediction_target import PredictionTarget, TargetKind
from ShadBotTrader.domain.common.errors import ValidationError

#: Loss + activation per task. Regression must NOT use a bounded
#: activation: a sigmoid output can never express a -3% low offset.
_TASK_HEADS: Dict[TargetKind, Dict[str, str]] = {
    TargetKind.PRICE_RANGE: {
        "activation": "linear",
        "loss": "mse",
        "metric": "mae",
    },
    TargetKind.TRADE_SIGNAL: {
        "activation": "softmax",
        "loss": "sparse_categorical_crossentropy",
        "metric": "accuracy",
    },
}


@dataclass(frozen=True)
class ModelRole:
    """One of the two models, fully specified."""

    name: str
    target: PredictionTarget
    model_id: str
    description: str
    window_size: int = 32

    def __post_init__(self) -> None:
        if self.window_size < 2:
            raise ValidationError("window_size must be >= 2")

    @property
    def output_units(self) -> int:
        return self.target.output_units

    @property
    def output_activation(self) -> str:
        return _TASK_HEADS[self.target.kind]["activation"]

    @property
    def loss(self) -> str:
        return _TASK_HEADS[self.target.kind]["loss"]

    @property
    def metric(self) -> str:
        return _TASK_HEADS[self.target.kind]["metric"]

    @property
    def timeframe(self) -> str:
        return self.target.timeframe

    @property
    def horizon(self) -> int:
        return self.target.horizon

    def to_dict(self) -> Dict[str, object]:
        return {
            "name": self.name,
            "model_id": self.model_id,
            "timeframe": self.timeframe,
            "horizon": self.horizon,
            "window_size": self.window_size,
            "output_units": self.output_units,
            "activation": self.output_activation,
            "loss": self.loss,
            "target": self.target.to_dict(),
        }


#: Timeframes that have their own trained models (Phase 39).
#: 1D was added alongside 1H so the platform can forecast a daily range,
#: which is a different question from an hourly one and deserves its own
#: weights rather than a rescaled reuse of the hourly model.
MODEL_TIMEFRAMES: tuple[str, ...] = ("5M", "1H", "1D")


def range_model_id(timeframe: str) -> str:
    """The model id for the range model of one timeframe.

    Each timeframe gets its OWN id. Sharing ``gold_range`` between 1H and
    1D would make the second training run overwrite the first, and the
    artifact store would hand back whichever was written last with no way
    to tell them apart.
    """
    return f"gold_range_{timeframe.strip().lower()}"


def range_model_role(
    timeframe: str = "1H",
    horizon: int = 5,
    window_size: int = 32,
) -> ModelRole:
    """The price-extremes model for one timeframe (1H or 1D)."""
    return ModelRole(
        name="range",
        target=PredictionTarget(
            kind=TargetKind.PRICE_RANGE,
            horizon=horizon,
            timeframe=timeframe,
        ),
        model_id=range_model_id(timeframe),
        description=(
            f"Predicts the highest high and lowest low over the next "
            f"{horizon} {timeframe} candles, as offsets from the current close."
        ),
        window_size=window_size,
    )


def signal_model_role(
    timeframe: str = "5M",
    horizon: int = 5,
    threshold: float = 0.0008,
    window_size: int = 32,
) -> ModelRole:
    """The direction model. Defaults to 5M bars, 5 candles ahead."""
    return ModelRole(
        name="signal",
        target=PredictionTarget(
            kind=TargetKind.TRADE_SIGNAL,
            horizon=horizon,
            timeframe=timeframe,
            threshold=threshold,
        ),
        model_id=f"gold_signal_{timeframe.strip().lower()}",
        description=(
            f"Predicts sell / hold / buy with probabilities over the next "
            f"{horizon} {timeframe} candles (neutral band {threshold:.4%})."
        ),
        window_size=window_size,
    )


def default_roles() -> Dict[str, ModelRole]:
    """Both roles, keyed by name."""
    return {"range": range_model_role(), "signal": signal_model_role()}
