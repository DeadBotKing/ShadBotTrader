"""Phase 29 demo — train the two predictive models.

    RANGE MODEL   1H candles  ->  highest high + lowest low, next N bars
    SIGNAL MODEL  5M candles  ->  buy / sell / hold with probabilities

    python scripts/run_dual_models.py                    # both, quick
    python scripts/run_dual_models.py --model range
    python scripts/run_dual_models.py --model signal --epochs 3
    python scripts/run_dual_models.py --symbol XAUUSD --with-features

Both models train roll-forward: each fold trains on a window and
validates on the window that immediately follows, so no future bar ever
influences a past prediction.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

STORAGE_ROOT = REPO_ROOT / "datasets"


def rule(title: str) -> None:
    print()
    print("=" * 74)
    print(f"  {title}")
    print("=" * 74)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Train the range and signal models (Phase 29).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD_i")
    parser.add_argument(
        "--model",
        choices=("both", "range", "signal"),
        default="both",
    )
    parser.add_argument("--range-timeframe", default="1H", help="range model candles")
    parser.add_argument("--signal-timeframe", default="5M", help="signal model candles")
    parser.add_argument("--horizon", type=int, default=5, help="candles to look ahead")
    parser.add_argument("--window", type=int, default=24, help="input window size")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--folds", type=int, default=2, help="roll-forward folds to keep")
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.0008,
        help="neutral band of the signal model, as a price fraction",
    )
    parser.add_argument(
        "--with-features",
        action="store_true",
        help="use the full 109-feature catalogue (slower)",
    )
    parser.add_argument("--storage-root", default=str(STORAGE_ROOT))
    return parser.parse_args(argv)


def load_candles(storage_root: Path, symbol: str, timeframe: str):
    """Load stored candles, generating a sample only when none exist."""
    from ShadBotTrader.data_cli import build_service, generate_sample
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe

    service, store, _ = build_service(storage_root)
    candles = store.query(Symbol(symbol), Timeframe(timeframe))
    if candles:
        return candles

    sample = storage_root / "samples" / f"{symbol}_{timeframe}.csv"
    if not sample.exists():
        generate_sample(symbol, timeframe, 600, sample)
    service.ingest(symbol, timeframe, str(sample))
    return store.query(Symbol(symbol), Timeframe(timeframe))


def build_service(args: argparse.Namespace):
    from ShadBotTrader.application.services.dual_model_service import DualModelService

    if not args.with_features:
        return DualModelService(include_features=False)

    from ShadBotTrader.infrastructure.feature.calculator_registry import (
        CalculatorRegistry,
    )
    from ShadBotTrader.infrastructure.feature.standard_catalog import (
        standard_feature_set,
    )

    return DualModelService(
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        include_features=True,
    )


def train_one(service, args, role, timeframe: str) -> int:
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe

    rule(f"{role.name.upper()} MODEL  ({timeframe} candles, {role.horizon} ahead)")
    print(f"  {role.description}")

    candles = load_candles(Path(args.storage_root), args.symbol, timeframe)
    print(f"\n  candles loaded : {len(candles)}")

    try:
        dataset = service.prepare(candles, Symbol(args.symbol), Timeframe(timeframe), role)
    except Exception as error:
        print(f"\n  [X] Cannot prepare data: {error}")
        return 1

    summary = dataset.summary()
    print(f"  usable rows    : {summary['rows']}")
    print(f"  feature columns: {summary['feature_columns']}")
    print(f"  dropped warmup : {summary['dropped_warmup']}")
    if summary["skipped_features"]:
        print(f"  skipped feats  : {summary['skipped_features']}")
    if dataset.label_distribution:
        print(f"  label balance  : {dataset.label_distribution}")
        if dataset.degenerate:
            print(
                "  [!] One class barely appears. A model trained here will "
                "learn to always answer the majority class."
            )

    try:
        import tensorflow  # noqa: F401
    except ImportError:
        print("\n  [i] TensorFlow is not installed, so training is skipped.")
        print("      Data preparation above is real and complete.")
        print("      Install with: pip install -r requirements-ai.txt")
        return 0

    print(f"\n  training roll-forward ({args.epochs} epoch(s), {args.folds} fold(s)) ...")
    outcome = service.train(
        candles,
        Symbol(args.symbol),
        Timeframe(timeframe),
        role,
        run_id=f"{role.name}-demo",
        epochs=args.epochs,
        max_folds=args.folds,
    )
    losses = outcome["fold_losses"]
    print(f"  fold losses    : {[round(value, 6) for value in losses]}")

    # ---- one live prediction so the output is concrete -----------------
    window = [row[: dataset.feature_count] for row in dataset.series[-role.window_size :]]
    last_close = float(candles[-1].close.amount)

    if role.name == "range":
        from ShadBotTrader.infrastructure.ai.dual_predictor import RangePredictor

        forecast = RangePredictor(horizon=role.horizon, timeframe=timeframe).forecast(
            outcome["artifact"], window, reference_close=last_close
        )
        print(f"\n  PREDICTION for the next {role.horizon} {timeframe} candles:")
        print(f"    current close  : {forecast.reference_close:.2f}")
        print(
            f"    highest high   : {forecast.predicted_high:.2f} " f"({forecast.high_offset:+.3%})"
        )
        print(f"    lowest low     : {forecast.predicted_low:.2f} " f"({forecast.low_offset:+.3%})")
        ratio = forecast.reward_risk()
        print(f"    reward / risk  : {'n/a' if ratio is None else f'{ratio:.2f}'}")
        if not forecast.is_coherent:
            print(
                "    [!] The model put its high BELOW its low. With this little "
                "training that is expected; it is reported, not hidden."
            )
    else:
        from ShadBotTrader.infrastructure.ai.dual_predictor import SignalPredictor

        forecast = SignalPredictor(horizon=role.horizon, timeframe=timeframe).forecast(
            outcome["artifact"], window
        )
        print(f"\n  PREDICTION for the next {role.horizon} {timeframe} candles:")
        print(f"    sell : {forecast.sell_probability:6.1%}")
        print(f"    hold : {forecast.hold_probability:6.1%}")
        print(f"    buy  : {forecast.buy_probability:6.1%}")
        print(f"    -> {forecast.describe()}")
        print(f"    actionable (>=60%): {forecast.is_actionable()}")

    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from ShadBotTrader.infrastructure.ai.model_roles import (
        range_model_role,
        signal_model_role,
    )

    print("=== ShadBotTrader — Phase 29 dual predictive models ===")
    print(f"symbol {args.symbol} | horizon {args.horizon} | window {args.window}")
    print(f"features: {'109-feature catalogue' if args.with_features else 'OHLCV only'}")

    service = build_service(args)
    status = 0

    if args.model in ("both", "range"):
        role = range_model_role(
            timeframe=args.range_timeframe,
            horizon=args.horizon,
            window_size=args.window,
        )
        status |= train_one(service, args, role, args.range_timeframe)

    if args.model in ("both", "signal"):
        role = signal_model_role(
            timeframe=args.signal_timeframe,
            horizon=args.horizon,
            threshold=args.threshold,
            window_size=args.window,
        )
        status |= train_one(service, args, role, args.signal_timeframe)

    rule("DONE")
    print("  Both models train roll-forward: no future bar influences a past")
    print("  prediction. Labels for the final N candles are dropped, never guessed.")
    return status


if __name__ == "__main__":
    sys.exit(main())
