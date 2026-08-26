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
    build_range_labels_seq2seq,
    RangeLabelsSeq2Seq,
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
    #: Explicit window ends for sparse first-passage signal labels.
    #: None means ordinary stride-1 windows (range model).
    sample_ends: Optional[List[int]] = None
    #: Raw matrix positions where each sample's future label ends. Signal
    #: labels are variable-horizon first-passage events, so a fixed purge
    #: gap alone cannot prove that a training label stayed before validation.
    sample_label_ends: Optional[List[int]] = None
    excluded_features: Dict[str, str] = field(default_factory=dict)

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
            "excluded_features": len(self.excluded_features),
            "excluded_feature_reasons": dict(self.excluded_features),
            "training_windows": (
                len(self.sample_ends)
                if self.sample_ends is not None
                else max(self.row_count - self.role.window_size + 1, 0)
            ),
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

        # model_role فیلتر می‌کنه که فیچرهای مناسب هر مدل وارد بشن
        _model_role = role.name  # "signal" یا "range"
        matrix = build_feature_matrix(
            candles=candles,
            symbol=symbol,
            timeframe=timeframe,
            feature_set=self._feature_set,
            resolver=self._resolver,
            include_features=self._include_features,
            causal_only=True,
            model_role=_model_role,
        )
        if matrix.is_empty:
            raise ValidationError(
                "The feature matrix is empty after warm-up. Provide more "
                "candles, or fewer features with long lookbacks."
            )

        distribution: Optional[Dict[str, int]] = None
        degenerate = False
        sample_ends: Optional[List[int]] = None
        sample_label_ends: Optional[List[int]] = None

        if role.target.kind is TargetKind.PRICE_RANGE:
            _use_seq2seq = getattr(role, "seq2seq", False)
            if _use_seq2seq:
                # فاز ۵۵: seq2seq labels — برای هر کندل t، offsets تا horizon k
                labels_s2s = build_range_labels_seq2seq(candles, horizon=role.horizon)
                targets = labels_s2s.to_flat_targets()
                target_names = labels_s2s.target_names()
                source_index = labels_s2s.source_index
            else:
                labels = build_range_labels(candles, horizon=role.horizon)
                targets = [
                    [high, low] for high, low in zip(labels.high_offset, labels.low_offset, strict=True)
                ]
                target_names = ["future_high_offset", "future_low_offset"]
                source_index = labels.source_index
            series, column_names, _ = attach_targets(
                matrix=matrix,
                targets=targets,
                target_source_index=source_index,
                target_names=target_names,
            )
        else:
            signal = build_signal_labels(
                candles,
                horizon=0,
                threshold=role.target.threshold,
                max_lookahead=None,
            )
            distribution = signal.distribution()
            degenerate = signal.is_degenerate()
            target_names = ["signal_class"]
            target_by_index = dict(zip(signal.source_index, signal.labels, strict=True))
            hit_by_index = dict(zip(signal.source_index, signal.hit_index, strict=True))
            original_to_matrix = {
                original: position for position, original in enumerate(matrix.source_index)
            }
            selected_signal_indices = [
                index
                for index in signal.source_index
                if index in original_to_matrix and original_to_matrix[index] >= role.window_size - 1
            ]
            sample_ends = [original_to_matrix[index] for index in selected_signal_indices]
            sample_label_ends = [
                original_to_matrix[hit_by_index[index]]
                for index in selected_signal_indices
                if hit_by_index[index] in original_to_matrix
            ]
            if len(sample_label_ends) != len(sample_ends):
                # A causal feature matrix should cover the whole available
                # candle history. Refuse an ambiguous label alignment rather
                # than silently training a variable-horizon target with a
                # guessed endpoint.
                raise ValidationError(
                    "Some first-passage label endpoints are outside the feature matrix"
                )
            if not sample_ends:
                raise ValidationError(
                    "No complete signal windows have a first-passage BUY/SELL label."
                )
            series = [
                list(row) + [float(target_by_index.get(original, 0))]
                for row, original in zip(matrix.rows, matrix.source_index, strict=True)
            ]
            column_names = list(matrix.column_names) + target_names

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
            sample_ends=sample_ends,
            sample_label_ends=sample_label_ends,
            excluded_features=dict(matrix.excluded_features),
        )

    # ------------------------------------------------------ training --
    def definition_for(
        self,
        role: ModelRole,
        dataset: PreparedDataset,
        version: int = 1,
        learning_rate: float = 1.5e-4,
    ) -> ModelDefinition:
        """The immutable contract the trainer must fulfil."""
        if learning_rate <= 0:
            raise ValidationError("learning_rate must be positive")
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
                "learning_rate": float(learning_rate),
                "loss": role.loss,
                "threshold": role.target.threshold,
                # Architecture — stored so the artifact can be rebuilt identically
                "n_filters": getattr(role, "n_filters", 32),
                "kernel_size": getattr(role, "kernel_size", 5),
                "n_layers_per_block": getattr(role, "n_layers_per_block", 4),
                "n_blocks": getattr(role, "n_blocks", 2),
                "depth_multiplier": getattr(role, "depth_multiplier", 8),
                "l2": float(getattr(role, "l2", 2.5e-4)),
                "dropout": float(getattr(role, "dropout", 0.10)),
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
        batch_size: int = 0,
        val_size: int = 0,
        step: int = 0,
        min_train_size: int = 0,
        max_folds: Optional[int] = None,
        progress: Any = None,
        initial_epoch: int = 0,
        resume_weights: "bytes | None" = None,
    ) -> Any:
        """A roll-forward WaveNet trainer configured for this role."""
        from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
            WavenetTrainer,
        )

        role = dataset.role
        is_regression = role.target.kind is TargetKind.PRICE_RANGE

        # Phase 39: the roll-forward geometry must scale with the data.
        # The old fixed defaults (val_size=4, step=2) were sized for the
        # few-hundred-row demo series; on 50,000 real candles they produce
        # 24,976 folds — each one a full model fit. That is not a slow
        # run, it is a run that never finishes, and it was the reason
        # training appeared to hang with no output.
        sample_ends = getattr(dataset, "sample_ends", None)
        rows = len(sample_ends) if sample_ends is not None else len(dataset.series)

        # Phase 44: batch size must scale with the data too. The old
        # fixed 8 was sized for the few-hundred-row demo series; on
        # 47,886 windows it means 5,986 gradient steps per epoch, each
        # one a full forward+backward pass over a 500x123 window. That
        # is ~1.4 hours for a SINGLE epoch, which reads as "hung" long
        # before it reads as "slow". A larger batch does the same work
        # in far fewer steps and uses the CPU's vector units properly.
        if not batch_size:
            if rows >= 20_000:
                batch_size = 64
            elif rows >= 5_000:
                batch_size = 32
            elif rows >= 1_000:
                batch_size = 16
            else:
                batch_size = 8

        if not val_size:
            val_size = max(4, min(2000, rows // 50))
        if not step:
            step = max(1, val_size)
        if not min_train_size:
            min_train_size = max(8, min(rows // 4, 20 * role.window_size))

        # Range labels are already joined to the usable feature rows, so
        # the trainer's ordinary sample index is the input-window end and
        # the target ends ``role.horizon`` candles later. Signal labels
        # carry their exact, variable first-passage endpoint from prepare().
        sample_label_ends = getattr(dataset, "sample_label_ends", None)
        if sample_label_ends is None and is_regression:
            sample_count = max(len(dataset.series) - role.window_size + 1, 0)
            sample_label_ends = [
                role.window_size - 1 + index + role.horizon for index in range(sample_count)
            ]

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
            sample_indices=getattr(dataset, "sample_ends", None),
            sample_label_ends=sample_label_ends,
            purge_gap=max(role.window_size - 1, 0) + (role.horizon if is_regression else 0),
            # Role-specific architecture hyperparameters
            n_filters=getattr(role, "n_filters", 32),
            kernel_size=getattr(role, "kernel_size", 5),
            n_layers_per_block=getattr(role, "n_layers_per_block", 4),
            n_blocks=getattr(role, "n_blocks", 2),
            depth_multiplier=getattr(role, "depth_multiplier", 8),
            l2=getattr(role, "l2", 2.5e-4),
            dropout=getattr(role, "dropout", 0.10),
            # Phase 50: resume from checkpoint
            initial_epoch=initial_epoch,
            resume_weights=resume_weights,
            # Phase 55: seq2seq head برای range model
            seq2seq=getattr(role, "seq2seq", False) if is_regression else False,
            horizon=role.horizon if is_regression else 5,
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
        on_epoch_model: Any = None,
        learning_rate: float = 1.5e-4,
        initial_epoch: int = 0,
        resume_weights: "bytes | None" = None,
    ) -> Dict[str, Any]:
        """Prepare, train and return the artifact plus its provenance.

        ``on_epoch_model`` is called ``(model, epoch, logs, total)`` after
        every epoch so the caller can checkpoint. Without it an
        interrupted run — a timeout, a closed lid — loses everything
        (Phase 46).

        ``initial_epoch`` and ``resume_weights`` enable Phase 50 resume:
        pass the bytes of a saved checkpoint and the epoch count already
        completed so training continues from that point.
        """
        dataset = self.prepare(candles, symbol, timeframe, role)
        definition = self.definition_for(role, dataset, learning_rate=learning_rate)
        trainer = self.build_trainer(
            dataset, epochs=epochs, max_folds=max_folds, progress=progress,
            initial_epoch=initial_epoch, resume_weights=resume_weights,
        )
        trainer.on_epoch_model = on_epoch_model

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
