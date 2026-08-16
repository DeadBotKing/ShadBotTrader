"""Demo run of the AI Platform without installing the package.

Trains a WaveNet direction classifier with roll-forward training on the
sample dataset and prints fold losses:

    python scripts/run_ai.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.data_cli import build_service as build_data_service  # noqa: E402
from ShadBotTrader.data_cli import generate_sample  # noqa: E402
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402

SYMBOL = "XAUUSD_i"
TIMEFRAME = "5M"
ROWS = 400


def main() -> int:
    storage_root = REPO_ROOT / "datasets"
    sample_path = storage_root / "samples" / f"{SYMBOL}_{TIMEFRAME}.csv"

    if not sample_path.exists():
        generate_sample(SYMBOL, TIMEFRAME, ROWS, sample_path)
    data_service, candle_store, _ = build_data_service(storage_root)
    candles = candle_store.query(Symbol(SYMBOL), Timeframe(TIMEFRAME))
    if not candles:
        data_service.ingest(SYMBOL, TIMEFRAME, str(sample_path))
        candles = candle_store.query(Symbol(SYMBOL), Timeframe(TIMEFRAME))

    from ShadBotTrader.application.services.model_training_service import (
        ModelTrainingService,
    )
    from ShadBotTrader.core.events.event_bus import EventBus
    from ShadBotTrader.domain.ai.model_definition import ModelDefinition
    from ShadBotTrader.domain.ai.model_identity import ModelId, ModelVersion
    from ShadBotTrader.domain.ai.model_types import ModelFamily, ModelType
    from ShadBotTrader.infrastructure.ai.dataset_builder import build_direction_series
    from ShadBotTrader.infrastructure.ai.filesystem_artifact_store import (
        FilesystemArtifactStore,
    )
    from ShadBotTrader.infrastructure.ai.in_memory_model_registry import (
        InMemoryModelRegistry,
    )
    from ShadBotTrader.infrastructure.ai.roll_forward_evaluator import RollForwardEvaluator
    from ShadBotTrader.infrastructure.ai.training_run_recorder import (
        InMemoryTrainingRunRepository,
    )
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
        WavenetPredictor,
        WavenetTrainer,
    )

    labeled = build_direction_series(candles)
    window_size = 16

    print("=== AI Platform demo ===")
    print(
        f"Dataset: {len(labeled.series)} labeled rows, "
        f"{len(labeled.feature_names)} columns, target=direction"
    )

    definition = ModelDefinition(
        model_id=ModelId("gold_direction"),
        version=ModelVersion(1),
        name="gold_direction direction classifier",
        model_type=ModelType.CLASSIFICATION,
        family=ModelFamily.WAVENET,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        target_name="direction",
        hyperparameters={
            "window_size": window_size,
            "epochs": 2,
            "learning_rate": 1.5e-4,
            "roll_forward": True,
        },
        input_schema={"window": window_size, "features": len(labeled.feature_names)},
        output_schema={"classes": 2},
        description="Wavenet direction classifier (roll-forward)",
    )

    trainer = WavenetTrainer(
        series=labeled.series,
        target_column=labeled.target_column,
        window_size=window_size,
        val_size=4,
        step=4,
        min_train_size=16,
        epochs=2,
        batch_size=8,
        output_units=2,
        seed=42,
        verbose=0,
    )

    registry = InMemoryModelRegistry()
    store = FilesystemArtifactStore(storage_root)
    service = ModelTrainingService(
        registry=registry,
        artifact_store=store,
        run_repository=InMemoryTrainingRunRepository(),
        event_bus=EventBus(),
    )

    predictor = WavenetPredictor()
    evaluator = RollForwardEvaluator(
        predictor=predictor,
        series=labeled.series,
        target_column=labeled.target_column,
        window_size=window_size,
        val_size=4,
        step=4,
        min_train_size=16,
        num_classes=2,
    )

    print(f"\nTraining Wavenet (roll-forward, {len(labeled.series)} rows) ...")
    outcome = service.train(
        definition=definition,
        trainer=trainer,
        evaluator=evaluator,
        dataset_version=1,
        seed=42,
    )

    print("\nTraining outcome:")
    print(f"  run_id    : {outcome.run_id}")
    print(f"  framework : {outcome.artifact.framework} {outcome.artifact.framework_version}")
    print(f"  checksum  : {outcome.checksum[:16]}...")
    print(f"  folds     : {len(trainer.fold_history)}")
    if trainer.fold_history:
        print(f"  fold val losses: {[round(loss, 4) for loss in trainer.fold_history]}")

    if outcome.evaluation:
        print(f"\nRoll-forward evaluation ({outcome.evaluation.fold_count} folds):")
        for name, value in outcome.evaluation.metrics.metrics.items():
            print(f"  {name:<12} {value:.4f}")

    print("\nAI Platform demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
