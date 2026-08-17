"""Application service: train and run the two Phase 29 models.

Composition root for the dual-model architecture. It owns no trading,
feature or AI logic of its own — it wires the pieces that already exist:

    candles -> feature matrix (109 features + OHLCV)
            -> forward labels  (future high/low  |  sell/hold/buy)
            -> aligned series
            -> roll-forward WaveNet training
            -> artifact

The range model reads 1H candles, the signal model reads 5M candles
(Phase 29 §2). Both are trained the same way, only the head differs.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

from ShadBotTrader.domain.ai.model_definition import ModelDefinition
from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
from ShadBotTrader.domain.ai.prediction_target import TargetKind
from ShadBotTrader.domain.ai.training_run import TrainingRun
from ShadBotTrader.domain.common.errors import ValidationError
from ShadBotTrader.domain.market.candle import Candle
from ShadBotTrader.domain.market.symbol import Symbol
from ShadBotTrader.domain.market.timeframe import Timeframe
from ShadBotTrader.infrastructure.ai.feature_matrix import (
    attach_targets,
    build_feature_matrix,
)
from ShadBotTrader.infrastructure.ai.model_roles import (
    ModelRole,
    range_model_role,
    signal_model_role,
)
from ShadBotTrader.infrastructure.ai.target_builder import (
    build_range_labels,
    build_signal_labels,
)


@dataclass
class PreparedDataset:
    """A labelled, aligned training matrix ready for the trainer."""

    series: List[List[float]]
    column_names: List[str]
    target_columns: List[int]
    role: ModelRole
    feature_count: int
    dropped_warmup: int
    skipped_features: List[str] = field(default_factory=list)
    label_distribution: Optional[Dict[str, int]] = None
    degenerate: bool = False

    @property
    def row_count(self) -> int:
        return len(self.series)

    def summary(self) -> Dict[str, Any]:
        return {
            "role": self.role.name,
            "timeframe": self.role.timeframe,
            "horizon": self.role.horizon,
            "rows": self.row_count,
            "feature_columns": self.feature_count,
            "target_columns": len(self.target_columns),
            "dropped_warmup": self.dropped_warmup,
            "skipped_features": len(self.skipped_features),
            "label_distribution": self.label_distribution,
            "degenerate": self.degenerate,
        }


class DualModelService:
    """Prepares data for, and trains, the range and signal models."""

    def __init__(
        self,
        feature_set: Any = None,
        resolver: Any = None,
        include_features: bool = True,
    ) -> None:
        """
        Args:
            feature_set: the Phase 12 catalogue. When omitted the models
                train on the six raw OHLCV columns only — a reduced
                input, never a fabricated one.
            resolver: calculator registry used to compute the catalogue.
            include_features: set False to deliberately train on OHLCV
                alone (useful to measure what the catalogue adds).
        """
        self._feature_set = feature_set
        self._resolver = resolver
        self._include_features = include_features

    # ---------------------------------------------------------- data --
    def prepare(
        self,
        candles: Sequence[Candle],
        symbol: Symbol,
        timeframe: Timeframe,
        role: ModelRole,
    ) -> PreparedDataset:
        """Build the aligned, labelled matrix for one role."""
        if len(candles) <= role.horizon + role.window_size:
            raise ValidationError(
                f"The {role.name} model needs more than "
                f"{role.horizon + role.window_size} candles "
                f"(horizon {role.horizon} + window {role.window_size}); "
                f"got {len(candles)}."
            )

        matrix = build_feature_matrix(
            candles=candles,
            symbol=symbol,
            timeframe=timeframe,
            feature_set=self._feature_set,
            resolver=self._resolver,
            include_features=self._include_features,
        )
        if matrix.is_empty:
            raise ValidationError(
                "The feature matrix is empty after warm-up. Provide more "
                "candles, or fewer features with long lookbacks."
            )

        distribution: Optional[Dict[str, int]] = None
        degenerate = False

        if role.target.kind is TargetKind.PRICE_RANGE:
            labels = build_range_labels(candles, horizon=role.horizon)
            targets = [
                [high, low] for high, low in zip(labels.high_offset, labels.low_offset, strict=True)
            ]
            target_names = ["future_high_offset", "future_low_offset"]
            source_index = labels.source_index
        else:
            signal = build_signal_labels(
                candles,
                horizon=role.horizon,
                threshold=role.target.threshold,
            )
            targets = [[float(value)] for value in signal.labels]
            target_names = ["signal_class"]
            source_index = signal.source_index
            distribution = signal.distribution()
            degenerate = signal.is_degenerate()

        series, column_names, _ = attach_targets(
            matrix=matrix,
            targets=targets,
            target_source_index=source_index,
            target_names=target_names,
        )

        if not series:
            raise ValidationError(
                "No rows survived the join between features and labels. The "
                "feature warm-up and the label horizon consumed the whole "
                "series."
            )

        feature_count = len(column_names) - len(target_names)
        target_columns = list(range(feature_count, len(column_names)))

        return PreparedDataset(
            series=series,
            column_names=column_names,
            target_columns=target_columns,
            role=role,
            feature_count=feature_count,
            dropped_warmup=matrix.dropped_warmup,
            skipped_features=matrix.skipped_features,
            label_distribution=distribution,
            degenerate=degenerate,
        )

    # ------------------------------------------------------ training --
    def definition_for(
        self,
        role: ModelRole,
        dataset: PreparedDataset,
        version: int = 1,
    ) -> ModelDefinition:
        """The immutable contract the trainer must fulfil."""
        is_regression = role.target.kind is TargetKind.PRICE_RANGE
        return ModelDefinition(
            model_id=ModelId(role.model_id),
            version=ModelVersion(version),
            name=f"{role.name}_wavenet",
            model_type=ModelType.REGRESSION if is_regression else ModelType.CLASSIFICATION,
            family=ModelFamily.WAVENET,
            feature_set_name="standard_v1" if self._include_features else "ohlcv_only",
            feature_set_version=1,
            target_name=("future_high_low" if is_regression else "signal_class"),
            hyperparameters={
                "window_size": role.window_size,
                "horizon": role.horizon,
                "timeframe": role.timeframe,
                "learning_rate": 1.5e-4,
                "loss": role.loss,
                "threshold": role.target.threshold,
            },
            input_schema={
                "window_size": role.window_size,
                "n_features": dataset.feature_count,
            },
            output_schema={
                "units": role.output_units,
                "activation": role.output_activation,
            },
            description=role.description,
        )

    def build_trainer(
        self,
        dataset: PreparedDataset,
        epochs: int = 2,
        batch_size: int = 8,
        val_size: int = 4,
        step: int = 2,
        min_train_size: int = 8,
        max_folds: Optional[int] = None,
        progress: Any = None,
    ) -> Any:
        """A roll-forward WaveNet trainer configured for this role."""
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
            WavenetTrainer,
        )

        role = dataset.role
        is_regression = role.target.kind is TargetKind.PRICE_RANGE

        return WavenetTrainer(
            series=dataset.series,
            target_column=dataset.target_columns[0],
            target_columns=dataset.target_columns if is_regression else None,
            window_size=role.window_size,
            val_size=val_size,
            step=step,
            min_train_size=min_train_size,
            epochs=epochs,
            batch_size=batch_size,
            output_units=role.output_units,
            output_activation=role.output_activation,
            loss=role.loss if is_regression else None,
            metric=role.metric if is_regression else None,
            max_folds=max_folds,
            progress=progress,
        )

    def train(
        self,
        candles: Sequence[Candle],
        symbol: Symbol,
        timeframe: Timeframe,
        role: ModelRole,
        run_id: str,
        epochs: int = 2,
        max_folds: Optional[int] = 3,
        progress: Any = None,
    ) -> Dict[str, Any]:
        """Prepare, train and return the artifact plus its provenance."""
        dataset = self.prepare(candles, symbol, timeframe, role)
        definition = self.definition_for(role, dataset)
        trainer = self.build_trainer(dataset, epochs=epochs, max_folds=max_folds, progress=progress)

        run = TrainingRun(
            run_id=run_id,
            model_id=definition.model_id,
            model_version=definition.version,
            dataset_version=1,
            feature_set_name=definition.feature_set_name,
            feature_set_version=definition.feature_set_version,
            seed=42,
            hyperparameters=dict(definition.hyperparameters),
        )
        artifact = trainer.train(definition, run)

        return {
            "role": role.name,
            "artifact": artifact,
            "definition": definition,
            "dataset": dataset.summary(),
            "fold_losses": list(trainer.fold_history),
            "fold_metrics": [dict(item) for item in getattr(trainer, "fold_metrics", [])],
        }


def default_service(feature_set: Any = None, resolver: Any = None) -> DualModelService:
    """A service wired to the standard catalogue when one is supplied."""
    return DualModelService(
        feature_set=feature_set,
        resolver=resolver,
        include_features=feature_set is not None and resolver is not None,
    )


__all__ = [
    "DualModelService",
    "PreparedDataset",
    "default_service",
    "range_model_role",
    "signal_model_role",
]
