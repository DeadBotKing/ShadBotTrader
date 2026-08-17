"""Demo run of the Data Platform without installing the package.

Adds ``src/`` to ``sys.path``, generates a sample CSV if needed, ingests
it end-to-end and prints the catalog plus a query result:

    python scripts/run_data.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC = REPO_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ShadBotTrader.data_cli import (  # noqa: E402
    build_service,
    generate_sample,
)
from ShadBotTrader.domain.market.symbol import Symbol  # noqa: E402
from ShadBotTrader.domain.market.timeframe import Timeframe  # noqa: E402

SYMBOL = "DEMOXAU"
TIMEFRAME = "5M"
ROWS = 300


def main() -> int:
    sample_path = REPO_ROOT / "datasets" / "samples" / f"{SYMBOL}_{TIMEFRAME}.csv"
    if not sample_path.exists():
        generate_sample(SYMBOL, TIMEFRAME, ROWS, sample_path)

    storage_root = REPO_ROOT / "datasets"
    service, store, catalog = build_service(storage_root)

    print("=== Data Platform demo ===")
    print(f"Ingesting {SYMBOL} {TIMEFRAME} from {sample_path.name} ...")
    result = service.ingest(SYMBOL, TIMEFRAME, str(sample_path))

    print(f"\nIngestion result (v{result.version}):")
    print(f"  raw rows      : {result.raw_row_count}")
    print(f"  valid candles : {result.candle_count}")
    print(f"  quality score : {result.quality_report.score.overall}")
    print(f"  quarantined   : {result.quarantined}")
    if result.quality_report.issues:
        print("  issues:")
        for issue in result.quality_report.issues:
            print(f"    [{issue.severity.value}] {issue.code}: {issue.message}")

    print("\n=== Catalog ===")
    for descriptor in catalog.list_all():
        print(
            f"  {descriptor.dataset_id.label} v{descriptor.version.number} "
            f"[{descriptor.status.value}] rows={descriptor.row_count}"
        )

    print("\n=== Query (first 3 candles) ===")
    candles = store.query(Symbol(SYMBOL), Timeframe(TIMEFRAME))[:3]
    for candle in candles:
        print(
            f"  {candle.open_time.value.isoformat()} "
            f"O={candle.open.amount} H={candle.high.amount} "
            f"L={candle.low.amount} C={candle.close.amount} V={candle.volume}"
        )

    print("\nData Platform demo finished successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
