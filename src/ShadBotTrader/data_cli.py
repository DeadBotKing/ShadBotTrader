"""CLI entrypoint for the Data Platform.

Commands:

    python -m ShadBotTrader.data_cli sample   --symbol XAUUSD_i --timeframe 5M --rows 200
    python -m ShadBotTrader.data_cli ingest   --csv PATH --symbol XAUUSD_i --timeframe 5M
    python -m ShadBotTrader.data_cli catalog

Real broker data (Windows + MetaTrader 5 terminal required):

    python -m ShadBotTrader.data_cli mt5-check
    python -m ShadBotTrader.data_cli mt5-symbols --pattern XAU
    python -m ShadBotTrader.data_cli mt5-ingest --symbol XAUUSD --timeframe 5M --bars 5000
"""

from __future__ import annotations

import argparse
import csv
import random
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, List

from ShadBotTrader.application.services.data_ingestion_service import DataIngestionService
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.domain.dataset.ports import (
    CandleRepository,
    DatasetRepository,
    MarketDataProvider,
)
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
    provider: MarketDataProvider | None = None,
) -> tuple[DataIngestionService, CandleRepository, DatasetRepository]:
    """Wire the concrete Data Platform components (composition root).

    ``provider`` defaults to the CSV reader; pass an ``Mt5MarketDataProvider``
    to ingest real broker history through the very same pipeline.
    """
    provider = provider or CsvMarketDataProvider()
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


# --------------------------------------------------------------- MT5 ------
def _mt5_provider(args: argparse.Namespace):
    """Build an MT5 provider from CLI credentials (all optional)."""
    from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
        Mt5MarketDataProvider,
    )

    return Mt5MarketDataProvider(
        login=getattr(args, "login", None),
        password=getattr(args, "password", None),
        server=getattr(args, "server", None),
        terminal_path=getattr(args, "terminal_path", None),
    )


def cmd_mt5_check(args: argparse.Namespace) -> int:
    """Verify the MetaTrader 5 connection before relying on it."""
    from ShadBotTrader.infrastructure.data import mt5_market_data_provider as mt5mod

    print("=== MetaTrader 5 connection check ===")
    if not mt5mod.is_available():
        print("  package        : NOT INSTALLED")
        print()
        print(mt5mod._INSTALL_HINT)
        return 1
    print("  package        : installed")

    provider = _mt5_provider(args)
    try:
        summary = provider.account_summary()
    except Exception as error:
        print(f"  terminal       : NOT CONNECTED\n\n  {error}")
        return 1
    finally:
        provider.shutdown()

    print("  terminal       : connected")
    for key, value in summary.items():
        print(f"  {key:<15}: {value}")
    print("\nReady. Try: shadbot-data mt5-symbols --pattern XAU")
    return 0


def cmd_mt5_symbols(args: argparse.Namespace) -> int:
    """List the instruments the terminal exposes."""
    provider = _mt5_provider(args)
    try:
        symbols = provider.available_symbols(args.pattern)
    finally:
        provider.shutdown()

    if not symbols:
        print(f"No symbols matched '{args.pattern}'.")
        print("Tip: make the instrument visible in the MT5 Market Watch window.")
        return 1

    print(f"{len(symbols)} symbol(s) matching '{args.pattern or '*'}':")
    for name in symbols[: args.limit]:
        print(f"  {name}")
    if len(symbols) > args.limit:
        print(f"  ... and {len(symbols) - args.limit} more (use --limit)")
    return 0


def _suggest_symbol(provider: Any, requested: str) -> None:
    """After a failed fetch, tell the user what the symbol is really called.

    Best-effort only: the ingest already failed, so a problem here must
    not replace the original error message with a new one.
    """
    from ShadBotTrader.infrastructure.data.mt5_symbol_resolver import resolve

    try:
        available = provider.available_symbols()
    except Exception:
        return
    report = resolve(requested, available)
    if report.found and not (report.best and report.best.is_exact):
        print()
        for line in report.advice():
            print(f"  {line}")


def cmd_mt5_resolve(args: argparse.Namespace) -> int:
    """Work out what this broker calls an instrument.

    Brokers rename the same instrument freely (XAUUSD.i, XAUUSDm, GOLD),
    which is the single most common reason a first real-data run fails.
    """
    from ShadBotTrader.infrastructure.data.mt5_symbol_resolver import resolve

    provider = _mt5_provider(args)
    try:
        available = provider.available_symbols()
    except Exception as error:
        print(f"Could not list symbols: {error}")
        return 1
    finally:
        provider.shutdown()

    report = resolve(args.symbol, available)
    print(f"=== Resolving '{args.symbol}' against {report.searched} broker symbols ===\n")

    if report.matches:
        for match in report.matches[: args.limit]:
            marker = "->" if match is report.best else "  "
            print(f"  {marker} {match.name:<22} {match.score:>3}  {match.reason}")
        print()

    for line in report.advice():
        print(f"  {line}")
    return 0 if report.found else 1


def cmd_mt5_ingest(args: argparse.Namespace) -> int:
    """Ingest real broker history through the standard pipeline."""
    storage_root = Path(args.storage_root)
    provider = _mt5_provider(args)

    try:
        service, _, _ = build_service(storage_root, provider=provider)
        print(f"Fetching {args.bars} bars of {args.symbol} {args.timeframe} from MT5 ...")
        result = service.ingest(args.symbol, args.timeframe, str(args.bars))
    except Exception as error:
        print(f"MT5 ingest failed: {error}")
        _suggest_symbol(provider, args.symbol)
        return 1
    finally:
        provider.shutdown()

    print(f"\nIngested {args.symbol} {args.timeframe} (v{result.version})")
    print("  provider      : mt5 (real broker data)")
    print(f"  raw rows      : {result.raw_row_count}")
    print(f"  valid candles : {result.candle_count}")
    print(f"  quality score : {result.quality_report.score.overall}")
    print(f"  quarantined   : {result.quarantined}")
    for issue in result.quality_report.issues:
        print(f"    [{issue.severity.value}] {issue.code}: {issue.message}")

    if result.quarantined:
        print("\nThe dataset was quarantined — inspect the issues above before use.")
    return 0


def cmd_mt5_timeframes(args: argparse.Namespace) -> int:
    """List the timeframes this provider understands."""
    from ShadBotTrader.infrastructure.data.mt5_market_data_provider import (
        supported_timeframes,
    )

    print("Supported timeframes:")
    print("  " + "  ".join(supported_timeframes()))
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

    def add_mt5_credentials(sub: argparse.ArgumentParser) -> None:
        sub.add_argument("--login", type=int, default=None, help="MT5 account number")
        sub.add_argument("--password", default=None, help="MT5 password")
        sub.add_argument("--server", default=None, help="MT5 broker server")
        sub.add_argument("--terminal-path", default=None, help="terminal64.exe path")

    mt5_check = subparsers.add_parser("mt5-check", help="verify the MT5 connection")
    add_mt5_credentials(mt5_check)
    mt5_check.set_defaults(func=cmd_mt5_check)

    mt5_symbols = subparsers.add_parser("mt5-symbols", help="list broker symbols")
    mt5_symbols.add_argument("--pattern", default="", help="e.g. XAU, EUR, *USD*")
    mt5_symbols.add_argument("--limit", type=int, default=60)
    add_mt5_credentials(mt5_symbols)
    mt5_symbols.set_defaults(func=cmd_mt5_symbols)

    mt5_resolve = subparsers.add_parser("mt5-resolve", help="find what your broker calls a symbol")
    mt5_resolve.add_argument("--symbol", required=True, help="e.g. XAUUSD or GOLD")
    mt5_resolve.add_argument("--limit", type=int, default=10)
    add_mt5_credentials(mt5_resolve)
    mt5_resolve.set_defaults(func=cmd_mt5_resolve)

    mt5_ingest = subparsers.add_parser("mt5-ingest", help="ingest real MT5 history")
    mt5_ingest.add_argument("--symbol", required=True, help="broker symbol, e.g. XAUUSD")
    mt5_ingest.add_argument("--timeframe", default="5M")
    mt5_ingest.add_argument("--bars", type=int, default=5000)
    mt5_ingest.add_argument("--storage-root", default=str(DEFAULT_STORAGE_ROOT))
    add_mt5_credentials(mt5_ingest)
    mt5_ingest.set_defaults(func=cmd_mt5_ingest)

    mt5_tf = subparsers.add_parser("mt5-timeframes", help="list supported timeframes")
    mt5_tf.set_defaults(func=cmd_mt5_timeframes)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
