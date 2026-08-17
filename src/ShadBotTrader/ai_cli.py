"""CLI entrypoint for the AI Platform.

Commands:

    python -m ShadBotTrader.ai_cli train    --model gold_direction --symbol XAUUSD --timeframe 5M
    python -m ShadBotTrader.ai_cli predict  --model gold_direction --version 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

DEFAULT_STORAGE_ROOT = Path("datasets")


def _load_candles(symbol: str, timeframe: str, storage_root: Path):
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore

    return ParquetCandleStore(storage_root).query(Symbol(symbol), Timeframe(timeframe))


def cmd_train(args: argparse.Namespace) -> int:
    storage_root = Path(args.storage_root)
    candles = _load_candles(args.symbol, args.timeframe, storage_root)
    if len(candles) < 20:
        print("Not enough candles — run the Data Platform demo first:")
        print("  python scripts/run_data.py")
        return 1

    _train_direction_model(candles, args.model, args.symbol, args.timeframe, storage_root, args)
    return 0


def _train_direction_model(
    candles, model_name: str, symbol: str, timeframe: str, storage_root: Path, args
) -> None:
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
    from ShadBotTrader.infrastructure.ai.training_run_recorder import (
        InMemoryTrainingRunRepository,
    )
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetTrainer

    labeled = build_direction_series(candles)
    window_size = min(args.window, len(labeled.series) - 1)

    definition = ModelDefinition(
        model_id=ModelId(model_name),
        version=ModelVersion(1),
        name=f"{model_name} direction classifier",
        model_type=ModelType.CLASSIFICATION,
        family=ModelFamily.WAVENET,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        target_name="direction",
        hyperparameters={
            "window_size": window_size,
            "epochs": args.epochs,
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
        val_size=max(2, window_size // 4),
        step=max(1, window_size // 4),
        min_train_size=max(8, window_size * 2),
        epochs=args.epochs,
        batch_size=8,
        output_units=2,
        seed=args.seed,
        verbose=0,
    )

    service = ModelTrainingService(
        registry=InMemoryModelRegistry(),
        artifact_store=FilesystemArtifactStore(storage_root),
        run_repository=InMemoryTrainingRunRepository(),
        event_bus=EventBus(),
    )

    outcome = service.train(
        definition=definition,
        trainer=trainer,
        evaluator=None,
        dataset_version=1,
        seed=args.seed,
    )

    print(f"Trained {model_name} v1")
    print(f"  run_id     : {outcome.run_id}")
    print(f"  framework  : {outcome.artifact.framework}")
    print(f"  checksum   : {outcome.checksum[:16]}...")
    print(f"  folds      : {len(trainer.fold_history)}")
    if trainer.fold_history:
        print(f"  fold losses: {[round(loss, 4) for loss in trainer.fold_history]}")


def cmd_predict(args: argparse.Namespace) -> int:
    storage_root = Path(args.storage_root)
    candles = _load_candles(args.symbol, args.timeframe, storage_root)

    from ShadBotTrader.domain.ai.inference import InferenceRequest

    # rebuild the registry the same way training registered it
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
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import WavenetPredictor

    labeled = build_direction_series(candles)
    window_size = min(args.window, len(labeled.series) - 1)
    definition = ModelDefinition(
        model_id=ModelId(args.model),
        version=ModelVersion(args.version),
        name=f"{args.model} direction classifier",
        model_type=ModelType.CLASSIFICATION,
        family=ModelFamily.WAVENET,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        target_name="direction",
        hyperparameters={"window_size": window_size, "epochs": 1, "learning_rate": 1.5e-4},
    )

    registry = InMemoryModelRegistry()
    registry.register(definition)
    store = FilesystemArtifactStore(storage_root)
    artifact = store.load(ModelId(args.model), ModelVersion(args.version))
    if artifact is None:
        print(f"No artifact for {args.model} v{args.version} — run train first.")
        return 1

    predictor = WavenetPredictor()
    request = InferenceRequest(
        model_id=args.model,
        model_version=args.version,
        features=[row[:-1] for row in labeled.series[-window_size:]],
        feature_names=labeled.feature_names[:-1],
    )
    prediction = predictor.predict(definition, artifact, request)
    label = "UP" if prediction.value >= 0.5 else "DOWN"
    print(
        f"Prediction: {label} (class={prediction.value}, "
        f"confidence={prediction.confidence:.4f})"
    )
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader AI Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    train = subparsers.add_parser("train", help="train a Wavenet direction classifier")
    train.add_argument("--model", default="gold_direction")
    train.add_argument("--symbol", default="XAUUSD")
    train.add_argument("--timeframe", default="5M")
    train.add_argument("--window", type=int, default=16)
    train.add_argument("--epochs", type=int, default=3)
    train.add_argument("--seed", type=int, default=42)
    train.add_argument("--storage-root", default=str(DEFAULT_STORAGE_ROOT))
    train.set_defaults(func=cmd_train)

    predict = subparsers.add_parser("predict", help="predict with a trained model")
    predict.add_argument("--model", default="gold_direction")
    predict.add_argument("--version", type=int, default=1)
    predict.add_argument("--symbol", default="XAUUSD")
    predict.add_argument("--timeframe", default="5M")
    predict.add_argument("--window", type=int, default=16)
    predict.add_argument("--storage-root", default=str(DEFAULT_STORAGE_ROOT))
    predict.set_defaults(func=cmd_predict)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
