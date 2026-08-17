"""Demo run of the AI Platform without installing the package.

Trains a WaveNet direction classifier with genuine roll-forward
(walk-forward) training on the sample dataset and prints a live view of
the training: learning rate, epochs, per-epoch loss/accuracy, the
current fold and step, plus elapsed/ETA timing.

    python scripts/run_ai.py --quick        # fast smoke run (~30s)
    python scripts/run_ai.py                # default demo
    python scripts/run_ai.py --folds 10     # cap the number of folds

Roll-forward trains ONE model per fold, so the run time grows linearly
with the fold count. ``--quick`` and ``--folds`` exist because the full
plan on the sample dataset is ~90 folds, which takes a long time on CPU.
"""

from __future__ import annotations

import argparse
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

SYMBOL = "DEMOXAU"
TIMEFRAME = "5M"
ROWS = 400


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="AI Platform demo (roll-forward WaveNet training).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--quick",
        action="store_true",
        help="fast smoke run: small model, few folds (~30s on CPU)",
    )
    parser.add_argument("--window-size", type=int, default=16, help="input window length")
    parser.add_argument("--epochs", type=int, default=2, help="epochs per fold")
    parser.add_argument("--learning-rate", type=float, default=1.5e-4, help="Adam learning rate")
    parser.add_argument("--batch-size", type=int, default=8, help="mini-batch size")
    parser.add_argument("--val-size", type=int, default=4, help="validation samples per fold")
    parser.add_argument("--step", type=int, default=4, help="fold growth step")
    parser.add_argument("--min-train-size", type=int, default=16, help="samples in the first fold")
    parser.add_argument(
        "--folds",
        type=int,
        default=None,
        help="cap the number of roll-forward folds (default: no cap)",
    )
    parser.add_argument("--seed", type=int, default=42, help="random seed")
    parser.add_argument(
        "--no-progress",
        action="store_true",
        help="disable the live training report",
    )
    parser.add_argument(
        "--no-epoch-lines",
        action="store_true",
        help="show only the per-fold progress bar, not per-epoch lines",
    )
    parser.add_argument(
        "--skip-evaluation",
        action="store_true",
        help="skip roll-forward evaluation (it reloads the model per sample)",
    )
    parser.add_argument(
        "--model-version",
        type=int,
        default=None,
        help="model version to write (default: next free version)",
    )
    return parser.parse_args(argv)


def next_free_version(storage_root: Path, model_id: str, start: int = 1) -> int:
    """Find the first unused artifact version.

    The artifact store is immutable by design: writing over an existing
    version raises. Re-running the demo therefore has to pick the next
    free slot instead of clobbering a previous run.
    """
    models_dir = storage_root / "models" / model_id
    version = start
    while (models_dir / f"v{version}.bin").exists():
        version += 1
    return version


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.quick:
        args.window_size = 8
        args.epochs = 2
        args.batch_size = 16
        args.val_size = 8
        args.step = 32
        args.min_train_size = 64
        if args.folds is None:
            args.folds = 5

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
    from ShadBotTrader.infrastructure.ai.roll_forward import expanding_split
    from ShadBotTrader.infrastructure.ai.roll_forward_evaluator import RollForwardEvaluator
    from ShadBotTrader.infrastructure.ai.training_progress import (
        ConsoleProgressReporter,
        NullProgressReporter,
    )
    from ShadBotTrader.infrastructure.ai.training_run_recorder import (
        InMemoryTrainingRunRepository,
    )
    from ShadBotTrader.infrastructure.ai.wavenet.wavenet_trainer import (
        WavenetPredictor,
        WavenetTrainer,
    )

    labeled = build_direction_series(candles)
    window_size = args.window_size
    model_version = args.model_version or next_free_version(storage_root, "gold_direction")

    print("=== AI Platform demo ===")
    print(
        f"Dataset: {len(labeled.series)} labeled rows, "
        f"{len(labeled.feature_names)} columns, target=direction"
    )

    # Report the plan up front so a long run is never a surprise.
    n_samples = max(len(labeled.series) - window_size + 1, 0)
    planned = expanding_split(
        total_length=n_samples,
        val_size=args.val_size,
        step=args.step,
        min_train_size=args.min_train_size,
    )
    planned_folds = len(planned.folds)
    effective_folds = min(planned_folds, args.folds) if args.folds else planned_folds
    if args.folds and planned_folds > args.folds:
        print(f"Roll-forward plan: {planned_folds} folds, capped to {args.folds} (--folds)")
    else:
        print(f"Roll-forward plan: {planned_folds} folds")
    print(f"Writing artifact as gold_direction v{model_version}")
    if effective_folds > 20 and not args.quick:
        print(
            f"  note: {effective_folds} folds means {effective_folds} independent model "
            f"fits.\n  Use --quick or --folds N for a faster run."
        )

    definition = ModelDefinition(
        model_id=ModelId("gold_direction"),
        version=ModelVersion(model_version),
        name="gold_direction direction classifier",
        model_type=ModelType.CLASSIFICATION,
        family=ModelFamily.WAVENET,
        feature_set_name="FXTradingFeatureSetV1",
        feature_set_version=1,
        target_name="direction",
        hyperparameters={
            "window_size": window_size,
            "epochs": args.epochs,
            "learning_rate": args.learning_rate,
            "roll_forward": True,
        },
        input_schema={"window": window_size, "features": len(labeled.feature_names)},
        output_schema={"classes": 2},
        description="Wavenet direction classifier (roll-forward)",
    )

    reporter = (
        NullProgressReporter()
        if args.no_progress
        else ConsoleProgressReporter(show_epochs=not args.no_epoch_lines)
    )

    trainer_kwargs = dict(
        series=labeled.series,
        target_column=labeled.target_column,
        window_size=window_size,
        val_size=args.val_size,
        step=args.step,
        min_train_size=args.min_train_size,
        epochs=args.epochs,
        batch_size=args.batch_size,
        output_units=2,
        seed=args.seed,
        verbose=0,
        progress=reporter,
        max_folds=args.folds,
    )
    if args.quick:
        trainer_kwargs.update(
            n_filters=8,
            kernel_size=3,
            n_layers_per_block=2,
            n_blocks=1,
            depth_multiplier=2,
        )

    trainer = WavenetTrainer(**trainer_kwargs)  # type: ignore[arg-type]

    registry = InMemoryModelRegistry()
    store = FilesystemArtifactStore(storage_root)
    service = ModelTrainingService(
        registry=registry,
        artifact_store=store,
        run_repository=InMemoryTrainingRunRepository(),
        event_bus=EventBus(),
    )

    evaluator = None
    if not args.skip_evaluation:
        evaluator = RollForwardEvaluator(
            predictor=WavenetPredictor(),
            series=labeled.series,
            target_column=labeled.target_column,
            window_size=window_size,
            val_size=args.val_size,
            step=args.step,
            min_train_size=args.min_train_size,
            num_classes=2,
            max_folds=args.folds,
        )

    outcome = service.train(
        definition=definition,
        trainer=trainer,
        evaluator=evaluator,
        dataset_version=1,
        seed=args.seed,
    )

    print("Training outcome:")
    print(f"  run_id    : {outcome.run_id}")
    print(f"  framework : {outcome.artifact.framework} {outcome.artifact.framework_version}")
    print(f"  checksum  : {outcome.checksum[:16]}...")
    print(f"  folds     : {len(trainer.fold_history)}")
    if trainer.fold_history:
        shown = [round(loss, 4) for loss in trainer.fold_history[:10]]
        suffix = " ..." if len(trainer.fold_history) > 10 else ""
        print(f"  fold val losses: {shown}{suffix}")

    if outcome.evaluation:
        print(f"\nRoll-forward evaluation ({outcome.evaluation.fold_count} folds):")
        for name, value in outcome.evaluation.metrics.metrics.items():
            print(f"  {name:<12} {value:.4f}")

    print("\nAI Platform demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
