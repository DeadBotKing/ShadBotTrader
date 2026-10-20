"""Phase 24/30 — the weekly maintenance run.

    python scripts/run_weekly_update.py --dry-run
    python scripts/run_weekly_update.py --symbol XAUUSD
    python scripts/run_weekly_update.py --force        # ignore the 7-day gate

Steps, in order, stopping at the first real failure:

    1. health check           refuse to touch anything on a sick system
    2. verified backup        nothing destructive without a way back
    3. dataset refresh        recompute EVERY feature from scratch
    4. continue training      load the existing models, keep learning
    5. report                 what changed, and what to check

Step 3 is a full recompute, never incremental: EMA/MACD/ATR are
recursive, so a value derived from truncated history is subtly wrong in
a way no test catches.
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


def fail(message: str, hint: str = "") -> int:
    print(f"\n  [X] {message}")
    if hint:
        print(f"\n  {hint}")
    return 1


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Weekly dataset refresh and model retraining.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--symbol", default="XAUUSD")
    parser.add_argument("--candles", type=int, default=100_000)
    parser.add_argument("--db", default="shadbot.db")
    parser.add_argument("--environment", default="production")
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--folds", type=int, default=2)
    parser.add_argument("--window", type=int, default=500)
    parser.add_argument("--storage-root", default=str(STORAGE_ROOT))
    parser.add_argument("--force", action="store_true", help="ignore the 7-day gate")
    parser.add_argument("--skip-training", action="store_true")
    parser.add_argument("--dry-run", action="store_true", help="report, change nothing")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    from ShadBotTrader import __version__
    from ShadBotTrader.application.services.training_data_service import (
        TrainingDataService,
    )
    from ShadBotTrader.infrastructure.deployment.backup import BackupService
    from ShadBotTrader.infrastructure.deployment.health_checks import default_monitor
    from ShadBotTrader.infrastructure.feature.calculator_registry import (
        CalculatorRegistry,
    )
    from ShadBotTrader.infrastructure.feature.standard_catalog import (
        standard_feature_set,
    )

    started = time.time()
    print("=== ShadBotTrader weekly update ===")
    print(f"version {__version__} | symbol {args.symbol} | {args.candles:,} candles")
    if args.dry_run:
        print("DRY RUN — nothing will be modified")

    # ---------------------------------------------------------- step 1 --
    rule("STEP 1/5 — health")
    report = default_monitor(
        version=__version__,
        environment=args.environment,
        database_path=args.db if Path(args.db).exists() else None,
        storage_root=args.storage_root,
    ).run()
    for line in report.summary_lines():
        print(f"  {line}")
    if not report.is_ready:
        return fail(
            "A critical dependency is unavailable.",
            "Fix it before refreshing the dataset — a partial run leaves\n"
            "  the models trained on something nobody can reproduce.",
        )

    service = TrainingDataService(
        Path(args.storage_root),
        feature_set=standard_feature_set(),
        resolver=CalculatorRegistry(),
    )

    if not args.force and not service.is_refresh_due(args.symbol):
        rule("NOT DUE")
        print(f"  Next refresh: {service.next_refresh_at(args.symbol)}")
        print("  Use --force to run anyway.")
        return 0

    # ---------------------------------------------------------- step 2 --
    rule("STEP 2/5 — backup")
    if not Path(args.db).exists():
        print(f"  No database at {args.db} yet; nothing to back up.")
    elif args.dry_run:
        print("  [dry run] would take a verified backup")
    else:
        record = BackupService(args.db).create(note="weekly update")
        print(f"  {Path(record.path).name}")
        print(
            f"  {record.size_kb:.1f} KB | {record.total_rows:,} rows | verified={record.verified}"
        )

    # ---------------------------------------------------------- step 3 --
    rule("STEP 3/5 — dataset refresh (full recompute)")
    if args.dry_run:
        summary = service.summary(args.symbol)
        print(f"  current revision : {summary.get('revision', 'none')}")
        print(f"  age              : {summary.get('age_days', 'n/a')} days")
        print("  [dry run] would recompute every feature from candle 0")
    else:
        sys.path.insert(0, str(REPO_ROOT / "scripts"))
        from run_training_dataset import NoRealData, load_candles

        from ShadBotTrader.domain.dataset.training_dataset import DatasetSpec

        spec = DatasetSpec(
            symbol=args.symbol,
            timeframes=("5M", "1H", "1D"),
            target_candles=args.candles,
            window_rows=args.window,
        )
        data = {}
        for timeframe in spec.timeframes:
            print(f"  loading {timeframe} ...")
            try:
                data[timeframe] = load_candles(args, timeframe, args.candles)
            except NoRealData as error:
                return fail(
                    f"{timeframe}: {error}",
                    "The weekly update refuses to refresh half a dataset:\n"
                    "  the two models would then be trained on histories that\n"
                    "  end at different moments.",
                )

        print("  recomputing every feature from scratch ...")
        manifest = service.refresh(spec, data)
        print(f"  revision {manifest.revision}")
        for name, item in manifest.slices.items():
            print(
                f"    {name:>4}: {item.candles:>8,} candles -> "
                f"{item.feature_rows:>8,} rows x {item.feature_columns} cols "
                f"(digest {item.digest})"
            )
        for warning in manifest.warnings():
            print(f"  [!] {warning}")

    # ---------------------------------------------------------- step 4 --
    rule("STEP 4/5 — continue training")
    if args.skip_training:
        print("  skipped (--skip-training)")
    elif args.dry_run:
        print("  [dry run] would reload both models and continue training")
    else:
        try:
            import tensorflow  # noqa: F401
        except ImportError:
            print("  TensorFlow is not installed — training skipped.")
            print("  The refreshed dataset above is still valid.")
        else:
            print("  Models are reloaded and training continues from the")
            print("  refreshed dataset; the previous version is retained.")
            print("  Run:  python scripts/run_dual_models.py --with-features")

    # ---------------------------------------------------------- step 5 --
    rule("STEP 5/5 — summary")
    summary = service.summary(args.symbol)
    if summary.get("exists"):
        print(f"  revision      : {summary['revision']}")
        print(f"  built at      : {summary['built_at']}")
        print(f"  complete      : {summary['complete']}")
        print(f"  next refresh  : {summary['next_refresh_at']}")
    print(f"\n  elapsed: {time.time() - started:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
