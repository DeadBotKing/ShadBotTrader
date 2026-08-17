"""Phase 30 — build, inspect and refresh the training dataset.

    python scripts/run_training_dataset.py --status
    python scripts/run_training_dataset.py --build --candles 100000
    python scripts/run_training_dataset.py --refresh
    python scripts/run_training_dataset.py --refresh --if-due
    python scripts/run_training_dataset.py --live-demo

The dataset holds 100,000 candles per timeframe (5M and 1H) with every
feature computed and stored, so training reads it instead of recomputing
each time. Windows of (500, 123) are generated lazily, stride 1.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

STORAGE_ROOT = REPO_ROOT / "datasets"


def rule(title: str) -> None:
    print()
    print("=" * 76)
    print(f"  {title}")
    print("=" * 76)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Training dataset and live buffer (Phase 30).",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD_i")
    parser.add_argument("--candles", type=int, default=100_000)
    parser.add_argument("--window", type=int, default=500)
    parser.add_argument("--horizon", type=int, default=5)
    parser.add_argument("--storage-root", default=str(STORAGE_ROOT))
    parser.add_argument("--build", action="store_true", help="build the dataset")
    parser.add_argument("--refresh", action="store_true", help="recompute everything")
    parser.add_argument(
        "--if-due",
        action="store_true",
        help="with --refresh: only run when a week has passed",
    )
    parser.add_argument("--status", action="store_true", help="show dataset state")
    parser.add_argument(
        "--live-demo", action="store_true", help="demonstrate the 800-candle buffer"
    )
    return parser.parse_args(argv)


def build_service(args: argparse.Namespace):
    from ShadBotTrader.application.services.training_data_service import (
        TrainingDataService,
    )
    from ShadBotTrader.infrastructure.feature.calculator_registry import (
        CalculatorRegistry,
    )
    from ShadBotTrader.infrastructure.feature.standard_catalog import (
        standard_feature_set,
    )

    return TrainingDataService(
        Path(args.storage_root),
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
    )


def load_candles(args: argparse.Namespace, timeframe: str, wanted: int):
    """Stored candles for a timeframe, generating a sample when absent."""
    from ShadBotTrader.data_cli import build_service as build_data_service
    from ShadBotTrader.data_cli import generate_sample
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe

    storage = Path(args.storage_root)
    service, store, _ = build_data_service(storage)
    candles = store.query(Symbol(args.symbol), Timeframe(timeframe))

    if len(candles) < wanted:
        sample = storage / "samples" / f"{args.symbol}_{timeframe}_{wanted}.csv"
        if not sample.exists():
            print(f"  generating {wanted:,} sample candles for {timeframe} ...")
            generate_sample(args.symbol, timeframe, wanted, sample)
        service.ingest(args.symbol, timeframe, str(sample))
        candles = store.query(Symbol(args.symbol), Timeframe(timeframe))

    return candles[-wanted:] if len(candles) > wanted else candles


def show_status(service, symbol: str) -> int:
    rule("DATASET STATUS")
    summary = service.summary(symbol)
    if not summary["exists"]:
        print(f"  No dataset for {symbol}.")
        print("  Build one:  python scripts/run_training_dataset.py --build")
        return 1

    print(f"  symbol        : {summary['symbol']}")
    print(f"  revision      : {summary['revision']}")
    print(f"  built at      : {summary['built_at']}")
    print(f"  age           : {summary['age_days']} days")
    print(f"  refresh due   : {summary['refresh_due']}")
    print(f"  next refresh  : {summary['next_refresh_at']}")
    print(f"  complete      : {summary['complete']}")
    print()
    for name, item in summary["slices"].items():
        print(
            f"  {name:>4}: {item['candles']:>8,} candles -> "
            f"{item['feature_rows']:>8,} rows x {item['feature_columns']} cols "
            f"(warmup {item['warmup_dropped']})"
        )
        print(f"        digest {item['digest']}  {item['first_time']} .. {item['last_time']}")

    for warning in summary["warnings"]:
        print(f"\n  [!] {warning}")
    return 0


def do_build(args: argparse.Namespace, service, refresh: bool) -> int:
    from ShadBotTrader.domain.dataset.training_dataset import DatasetSpec

    action = "REFRESH" if refresh else "BUILD"
    rule(f"{action} — {args.candles:,} candles per timeframe")

    if refresh and args.if_due and not service.is_refresh_due(args.symbol):
        print(f"  Not due yet. Next refresh: {service.next_refresh_at(args.symbol)}")
        return 0

    spec = DatasetSpec(
        symbol=args.symbol,
        timeframes=("5M", "1H"),
        target_candles=args.candles,
        window_rows=args.window,
    )

    data = {}
    for timeframe in spec.timeframes:
        print(f"\n  loading {timeframe} ...")
        candles = load_candles(args, timeframe, args.candles)
        print(f"    {len(candles):,} candles")
        data[timeframe] = candles

    print("\n  computing every feature from scratch (recursive indicators")
    print("  make incremental updates unsafe) ...")
    started = time.time()
    manifest = service.refresh(spec, data) if refresh else service.build(spec, data)
    print(f"  done in {time.time() - started:.1f}s\n")

    for name, item in manifest.slices.items():
        print(
            f"  {name:>4}: {item.candles:>8,} candles -> "
            f"{item.feature_rows:>8,} rows x {item.feature_columns} cols"
        )
        print(
            f"        stride-1 windows of ({args.window} x {item.feature_columns}): "
            f"{item.usable_windows(args.window, args.horizon):,}"
        )

    for warning in manifest.warnings():
        print(f"\n  [!] {warning}")

    if refresh:
        print("\n  Models should now be reloaded and training continued on")
        print("  this revision:  python scripts/run_dual_models.py --with-features")
    return 0


def live_demo(args: argparse.Namespace) -> int:
    from ShadBotTrader.infrastructure.ai.live_matrix import LiveMatrixBuilder
    from ShadBotTrader.infrastructure.data.live_buffer import LiveMarketData
    from ShadBotTrader.infrastructure.feature.calculator_registry import (
        CalculatorRegistry,
    )
    from ShadBotTrader.infrastructure.feature.standard_catalog import (
        standard_feature_set,
    )

    rule("LIVE BUFFER — 800 candles, self-maintaining")

    live = LiveMarketData(timeframes=("5M", "1H"))
    builder = LiveMatrixBuilder(
        args.symbol,
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
        window_rows=args.window,
    )

    for timeframe in ("5M", "1H"):
        candles = load_candles(args, timeframe, 900)
        tally = live.prime(timeframe, candles)
        buffer = live.buffer(timeframe)
        print(f"\n  {timeframe}: primed with {len(candles)} candles -> {tally}")
        print(f"    buffer holds {buffer.size} (capacity {buffer.capacity})")

        window, reason = builder.try_build(buffer)
        if window is None:
            print(f"    [!] {reason}")
            continue
        print(f"    model input : {window.shape[0]} rows x {window.shape[1]} columns")
        print(f"    last candle : {window.last_timestamp}")
        print(f"    close       : {window.reference_close}")

    print("\n  Every 5 minutes: push one new candle per timeframe. The buffer")
    print("  evicts the oldest, recomputes features and re-exposes the newest")
    print(f"  {args.window} rows. Nothing else changes.")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    service = build_service(args)

    print("=== ShadBotTrader — Phase 30 training dataset & live buffer ===")
    print(f"symbol {args.symbol} | window {args.window} rows | horizon {args.horizon}")

    if args.live_demo:
        return live_demo(args)
    if args.build:
        return do_build(args, service, refresh=False)
    if args.refresh:
        return do_build(args, service, refresh=True)
    return show_status(service, args.symbol)


if __name__ == "__main__":
    sys.exit(main())
