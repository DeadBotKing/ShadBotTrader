"""CLI entrypoint for the Data Platform.

Commands:

    python -m ShadBotTrader.data_cli sample   --symbol XAUUSD_i --timeframe 5M --rows 200
    python -m ShadBotTrader.data_cli ingest   --csv PATH --symbol XAUUSD_i --timeframe 5M
    python -m ShadBotTrader.data_cli catalog
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from ShadBotTrader.application.services.data_ingestion_service import DataIngestionService
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.dataset.ports import CandleRepository, DatasetRepository
from ShadBotTrader.infrastructure.data.candle_normalizer import CandleNormalizer
from ShadBotTrader.infrastructure.data.candle_validator import CandleValidator
from ShadBotTrader.infrastructure.data.csv_market_data_provider import CsvMarketDataProvider
from ShadBotTrader.infrastructure.data.in_memory_dataset_catalog import (
    InMemoryDatasetRepository,
)
from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore
from ShadBotTrader.infrastructure.data.quality_analyzer import QualityAnalyzer

DEFAULT_STORAGE_ROOT = Path("datasets")
DEFAULT_SAMPLE_DIR = Path("datasets") / "samples"


def build_service(
    storage_root: Path = DEFAULT_STORAGE_ROOT,
) -> tuple[DataIngestionService, CandleRepository, DatasetRepository]:
    """Wire the concrete Data Platform components (composition root)."""
    provider = CsvMarketDataProvider()
    store = ParquetCandleStore(storage_root)
    catalog = InMemoryDatasetRepository()
    event_bus = EventBus()
    service = DataIngestionService(
        provider=provider,
        validator=CandleValidator(),
        normalizer=CandleNormalizer(),
        quality_analyzer=QualityAnalyzer(),
        candle_repository=store,
        dataset_repository=catalog,
        event_bus=event_bus,
    )
    return service, store, catalog


def generate_sample(symbol: str, timeframe: str, rows: int, out: Path) -> Path:
    """Generate a deterministic sample candle CSV for demos and tests."""
    step = _timeframe_step(timeframe)
    start = datetime(2024, 1, 2, 8, 0, tzinfo=timezone.utc)
    rng = random.Random(42)
    price = 2000.0

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=["timestamp", "open", "high", "low", "close", "volume"]
        )
        writer.writeheader()
        for index in range(rows):
            open_price = price
            close_price = price + rng.uniform(-2.0, 2.0)
            high = max(open_price, close_price) + rng.uniform(0.2, 1.5)
            low = min(open_price, close_price) - rng.uniform(0.2, 1.5)
            volume = int(rng.uniform(80, 400))
            timestamp = (start + index * step).strftime("%Y-%m-%d %H:%M:%S")
            writer.writerow(
                {
                    "timestamp": timestamp,
                    "open": f"{open_price:.2f}",
                    "high": f"{high:.2f}",
                    "low": f"{low:.2f}",
                    "close": f"{close_price:.2f}",
                    "volume": str(volume),
                }
            )
            price = close_price
    return out


def _timeframe_step(timeframe: str) -> timedelta:
    unit = timeframe[-1].upper()
    amount = int(timeframe[:-1])
    if unit == "M":
        return timedelta(minutes=amount)
    if unit == "H":
        return timedelta(hours=amount)
    if unit == "D":
        return timedelta(days=amount)
    raise ValueError(f"Unsupported timeframe: {timeframe}")


def cmd_sample(args: argparse.Namespace) -> int:
    out = generate_sample(args.symbol, args.timeframe, args.rows, Path(args.out))
    print(f"Sample CSV written to {out}")
    return 0


def cmd_ingest(args: argparse.Namespace) -> int:
    storage_root = Path(args.storage_root)
    service, store, catalog = build_service(storage_root)
    result = service.ingest(args.symbol, args.timeframe, args.csv)

    print(f"Ingested {args.symbol} {args.timeframe} (v{result.version})")
    print(f"  raw rows      : {result.raw_row_count}")
    print(f"  valid candles : {result.candle_count}")
    print(f"  quality score : {result.quality_report.score.overall}")
    print(f"  quarantined   : {result.quarantined}")
    for issue in result.quality_report.issues:
        print(f"    [{issue.severity.value}] {issue.code}: {issue.message}")
    return 0


def cmd_catalog(args: argparse.Namespace) -> int:
    storage_root = Path(args.storage_root)
    _, _, catalog = build_service(storage_root)
    descriptors = catalog.list_all()
    if not descriptors:
        print("Catalog is empty.")
        return 0
    print(f"Datasets in catalog ({len(descriptors)}):")
    for descriptor in descriptors:
        print(
            f"  {descriptor.dataset_id.label} v{descriptor.version.number} "
            f"[{descriptor.status.value}] rows={descriptor.row_count}"
        )
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader Data Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    sample = subparsers.add_parser("sample", help="generate a sample candle CSV")
    sample.add_argument("--symbol", default="XAUUSD_i")
    sample.add_argument("--timeframe", default="5M")
    sample.add_argument("--rows", type=int, default=200)
    sample.add_argument("--out", default=str(DEFAULT_SAMPLE_DIR / "XAUUSD_i_5M.csv"))
    sample.set_defaults(func=cmd_sample)

    ingest = subparsers.add_parser("ingest", help="ingest a candle CSV")
    ingest.add_argument("--csv", required=True)
    ingest.add_argument("--symbol", required=True)
    ingest.add_argument("--timeframe", required=True)
    ingest.add_argument("--storage-root", default=str(DEFAULT_STORAGE_ROOT))
    ingest.set_defaults(func=cmd_ingest)

    catalog = subparsers.add_parser("catalog", help="list registered datasets")
    catalog.add_argument("--storage-root", default=str(DEFAULT_STORAGE_ROOT))
    catalog.set_defaults(func=cmd_catalog)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
