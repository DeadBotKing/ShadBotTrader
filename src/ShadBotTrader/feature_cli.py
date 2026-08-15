"""CLI entrypoint for the Feature Platform.

Commands:

    python -m ShadBotTrader.feature_cli list
    python -m ShadBotTrader.feature_cli compute --symbol XAUUSD_i --timeframe 5M
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List

from ShadBotTrader.application.services.feature_computation_service import (
    FeatureComputationService,
)
from ShadBotTrader.core.events.event_bus import EventBus
from ShadBotTrader.infrastructure.feature.calculator_registry import CalculatorRegistry
from ShadBotTrader.infrastructure.feature.in_memory_feature_registry import (
    InMemoryFeatureRegistry,
)
from ShadBotTrader.infrastructure.feature.parquet_feature_store import ParquetFeatureStore
from ShadBotTrader.infrastructure.feature.standard_catalog import standard_feature_set_v1

DEFAULT_STORAGE_ROOT = Path("datasets")


def _build_service(storage_root: Path):
    store = ParquetFeatureStore(storage_root)
    registry = InMemoryFeatureRegistry()
    event_bus = EventBus()
    service = FeatureComputationService(
        calculator_resolver=CalculatorRegistry(),
        registry=registry,
        repository=store,
        event_bus=event_bus,
    )
    return service, store, registry


def cmd_list(args: argparse.Namespace) -> int:
    feature_set = standard_feature_set_v1()
    print(f"Feature set: {feature_set.name} v{feature_set.version.number}")
    for definition in feature_set.definitions:
        live = "live" if definition.is_live_compatible else "research-only"
        print(
            f"  {definition.feature_id.value:<20} {definition.name:<22} "
            f"lookback={definition.lookback:<3} [{live}]"
        )
    return 0


def cmd_compute(args: argparse.Namespace) -> int:
    storage_root = Path(args.storage_root)
    service, store, registry = _build_service(storage_root)

    # Load candles from the Data Platform Parquet store
    from ShadBotTrader.domain.market.symbol import Symbol
    from ShadBotTrader.domain.market.timeframe import Timeframe
    from ShadBotTrader.infrastructure.data.parquet_candle_store import ParquetCandleStore

    candle_store = ParquetCandleStore(storage_root)
    candles = candle_store.query(Symbol(args.symbol), Timeframe(args.timeframe))
    if not candles:
        print(f"No candles found for {args.symbol} {args.timeframe}.")
        print("Run the Data Platform demo first: python scripts/run_data.py")
        return 1

    feature_set = standard_feature_set_v1()
    result = service.compute_set(
        feature_set=feature_set,
        symbol=Symbol(args.symbol),
        timeframe=Timeframe(args.timeframe),
        candles=candles,
        source_dataset_id=f"csv.market_candle.{args.symbol}.{args.timeframe}.L3_normalized",
        dataset_version=1,
    )

    print(f"Computed feature set {result.set_name} for {result.symbol} {result.timeframe}")
    print(f"  candles    : {len(candles)}")
    for outcome in result.outcomes:
        status = "QUARANTINED" if outcome.quarantined else f"v{outcome.version}"
        live = "live" if outcome.live_compatible else "research"
        print(
            f"  {outcome.feature_id:<20} {status:<12} "
            f"available={outcome.available_count:<5} score={outcome.quality.score.overall} [{live}]"
        )
    return 0


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ShadBotTrader Feature Platform CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="list the standard feature set")
    list_parser.set_defaults(func=cmd_list)

    compute = subparsers.add_parser("compute", help="compute the standard feature set")
    compute.add_argument("--symbol", default="XAUUSD_i")
    compute.add_argument("--timeframe", default="5M")
    compute.add_argument("--storage-root", default=str(DEFAULT_STORAGE_ROOT))
    compute.set_defaults(func=cmd_compute)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
